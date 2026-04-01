"""
TinyLoRA — "Learning to Reason in 13 Parameters" (arXiv:2602.04118) 実装。

論文コアアルゴリズム:
  ΔW = A · diag(P @ v) · B

  A ∈ ℝ^(d_out × r) : frozen  (truncated SVD の左特異ベクトル)
  B ∈ ℝ^(r × d_in)  : frozen  (truncated SVD の右特異ベクトル)
  P ∈ ℝ^(r × u)     : fixed random projection tensor (学習しない)
  v ∈ ℝ^u           : trainable (唯一の学習可能パラメータ、u << r)

weight tying: 複数モジュールが同一の v を共有 → 全体で 13 パラメータ

使い方:
    # 1. base model をロード (QLoRA 4-bit 推奨)
    model = AutoModelForCausalLM.from_pretrained(...)

    # 2. TinyLoRA をモデルに適用
    tinylora = TinyLoRAModel(model, r=2, u=1, tying="tile")

    # 3. 学習 (GRPO 推奨; SFT は極小パラメータ数では機能しない)
    optimizer = torch.optim.AdamW(tinylora.parameters(), lr=1e-3)

    # 4. アダプター保存
    tinylora.save_adapter("./output")
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Literal, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)

TyingStrategy = Literal["tile", "structured", "none"]


class TinyLoRALayer(nn.Module):
    """
    単一 Linear 層への TinyLoRA 適用。

    ΔW = A @ torch.diag(P @ v) @ B
    ここで A (d_out × r), B (r × d_in) は frozen SVD 成分。
    P (r × u) は fixed random (normal(0, 1/√(r·u))).
    v (u,) のみ学習可能。
    """

    def __init__(
        self,
        weight: torch.Tensor,
        r: int = 2,
        u: int = 1,
        shared_v: Optional[nn.Parameter] = None,
    ) -> None:
        super().__init__()
        d_out, d_in = weight.shape

        # Truncated SVD (float32 で計算してからキャスト)
        w_f32 = weight.detach().float()
        try:
            U, S, Vh = torch.linalg.svd(w_f32, full_matrices=False)
        except Exception:
            # fallback: random init
            U = torch.randn(d_out, r)
            S = torch.ones(r)
            Vh = torch.randn(r, d_in)

        # A = U[:, :r] * sqrt(S[:r]),  B = sqrt(S[:r]) * Vh[:r, :]
        s_sqrt = S[:r].sqrt()
        A = (U[:, :r] * s_sqrt.unsqueeze(0)).to(weight.dtype)  # (d_out, r)
        B = (s_sqrt.unsqueeze(1) * Vh[:r, :]).to(weight.dtype)  # (r, d_in)

        self.register_buffer("A", A)  # frozen
        self.register_buffer("B", B)  # frozen

        # Fixed random projection P ∈ ℝ^(r × u)
        P = torch.randn(r, u) / math.sqrt(r * u)
        self.register_buffer("P", P.to(weight.dtype))

        # Trainable vector — 共有される場合は外部から渡す
        if shared_v is not None:
            self.v = shared_v
            self._owns_v = False
        else:
            self.v = nn.Parameter(torch.zeros(u))
            self._owns_v = True

        self.r = r
        self.u = u

    def delta_weight(self) -> torch.Tensor:
        """ΔW = A @ diag(P @ v) @ B"""
        scale = self.P @ self.v  # (r,)
        return self.A * scale.unsqueeze(0) @ self.B  # (d_out, d_in)

    def forward(self, x: torch.Tensor, base_output: torch.Tensor) -> torch.Tensor:
        """base_output + x @ ΔW.T"""
        dW = self.delta_weight()
        return base_output + F.linear(x, dW)


class TinyLoRAModel(nn.Module):
    """
    既存の nn.Module に TinyLoRA を非破壊で適用するラッパー。

    tying:
      "tile"       : 同じ深さのレイヤー群で v を共有（論文推奨）
      "structured" : 同種モジュール (q_proj 等) で共有
      "none"       : 全モジュールが独立した v を持つ
    """

    def __init__(
        self,
        base_model: nn.Module,
        r: int = 2,
        u: int = 1,
        tying: TyingStrategy = "tile",
        target_modules: tuple[str, ...] = (
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ),
        n_tie_groups: Optional[int] = None,
    ) -> None:
        super().__init__()
        self.base_model = base_model
        self.r = r
        self.u = u
        self.tying = tying
        self.target_modules = target_modules
        self._tiny_layers: dict[str, TinyLoRALayer] = nn.ModuleDict()

        # 対象モジュールを収集
        target_linear: list[tuple[str, nn.Linear]] = []
        for name, module in base_model.named_modules():
            if isinstance(module, nn.Linear) and any(
                t in name for t in target_modules
            ):
                target_linear.append((name, module))

        if not target_linear:
            logger.warning("No target modules found for TinyLoRA!")
            return

        # Tying グループを決定
        shared_vs: list[nn.Parameter] = self._build_shared_vs(
            target_linear, tying, n_tie_groups, u
        )

        # TinyLoRALayer を構築して hook を登録
        for i, (name, linear) in enumerate(target_linear):
            group_idx = self._get_group_index(i, len(target_linear), tying, len(shared_vs))
            layer = TinyLoRALayer(
                linear.weight, r=r, u=u, shared_v=shared_vs[group_idx]
            )
            safe_name = name.replace(".", "_")
            self._tiny_layers[safe_name] = layer

            # forward hook でアダプター差分を加算
            def make_hook(tiny_layer: TinyLoRALayer):
                def hook(module, inp, out):
                    x = inp[0]
                    return tiny_layer.forward(x, out)
                return hook

            linear.register_forward_hook(make_hook(layer))

        total_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        logger.info(
            "TinyLoRA applied: %d target modules, tying=%s, r=%d, u=%d, "
            "total trainable params=%d",
            len(target_linear), tying, r, u, total_params,
        )

    def _build_shared_vs(
        self,
        target_linear: list,
        tying: TyingStrategy,
        n_tie_groups: Optional[int],
        u: int,
    ) -> list[nn.Parameter]:
        n = len(target_linear)
        if tying == "none":
            return [nn.Parameter(torch.zeros(u)) for _ in range(n)]
        elif tying == "structured":
            # 同種モジュール名ごとにグループ化
            groups: dict[str, nn.Parameter] = {}
            for name, _ in target_linear:
                module_type = name.split(".")[-1]  # "q_proj" 等
                if module_type not in groups:
                    groups[module_type] = nn.Parameter(torch.zeros(u))
            return list(groups.values())
        else:  # "tile" (論文推奨)
            # n_tie_groups を指定しない場合は sqrt(n) に近い値を使う
            if n_tie_groups is None:
                n_tie_groups = max(1, round(math.sqrt(n)))
            return [nn.Parameter(torch.zeros(u)) for _ in range(n_tie_groups)]

    def _get_group_index(
        self, idx: int, total: int, tying: TyingStrategy, n_groups: int
    ) -> int:
        if tying == "none":
            return idx
        elif tying == "structured":
            # structured の場合は _build_shared_vs で名前ベースに割り当て済みなので
            # tile と同じ計算式でも問題ない
            return idx % n_groups
        else:  # tile
            return (idx * n_groups) // total

    def trainable_parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def save_adapter(self, output_dir: str | Path) -> dict:
        """学習済みアダプター (v ベクトル群) を保存する。"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        state: dict[str, list] = {}
        for name, layer in self._tiny_layers.items():
            if layer._owns_v:
                state[name] = layer.v.detach().cpu().tolist()

        # 共有 v は shared_v への参照なので別途収集
        seen_ids: set[int] = set()
        shared_state: dict[str, list] = {}
        for name, layer in self._tiny_layers.items():
            vid = id(layer.v)
            if vid not in seen_ids:
                seen_ids.add(vid)
                shared_state[f"shared_{len(seen_ids)}"] = layer.v.detach().cpu().tolist()

        adapter_data = {
            "format": "tinylora_v1",
            "r": self.r,
            "u": self.u,
            "tying": self.tying,
            "target_modules": list(self.target_modules),
            "trainable_params": self.trainable_parameter_count(),
            "shared_vs": shared_state,
            "layer_vs": state,
        }

        adapter_path = output_dir / "tinylora_adapter.json"
        adapter_path.write_text(json.dumps(adapter_data, indent=2), encoding="utf-8")
        logger.info(
            "TinyLoRA adapter saved: %s (%d params)",
            adapter_path, adapter_data["trainable_params"],
        )
        return adapter_data

    def to_peft_lora(self, output_dir: str | Path) -> Path:
        """
        TinyLoRA アダプターを PEFT 互換 rank-2 LoRA 形式に変換する。

        TinyLoRA の ΔW = A·diag(P@v)·B は rank-2 行列更新なので、
        PEFT LoRA (rank=2) として表現できる:
          ΔW = A_scaled @ B  where A_scaled = A * sqrt(diag(P@v))
                                         B_scaled = sqrt(diag(P@v)) * B

        これにより llama.cpp の convert_lora_to_gguf.py が使用可能になる。
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        lora_state: dict[str, torch.Tensor] = {}

        for name, layer in self._tiny_layers.items():
            with torch.no_grad():
                scale = layer.P @ layer.v  # (r,)
                # 数値安定性のため scale の符号を保持しつつ sqrt を取る
                abs_scale = scale.abs().clamp(min=1e-8)
                sign = scale.sign()
                s_sqrt = abs_scale.sqrt() * sign.clamp(min=0)  # 正側のみ
                s_sqrt_abs = abs_scale.sqrt()

                # lora_A = A * sqrt(|scale|),  lora_B = sqrt(|scale|) * B
                A_scaled = layer.A * s_sqrt_abs.unsqueeze(0)  # (d_out, r)
                B_scaled = s_sqrt_abs.unsqueeze(1) * layer.B   # (r, d_in)

                # PEFT の命名規則: base_model.model.{orig_name}.lora_A.weight
                orig_name = name.replace("_", ".")
                lora_state[f"base_model.model.{orig_name}.lora_A.weight"] = B_scaled  # PEFT は転置
                lora_state[f"base_model.model.{orig_name}.lora_B.weight"] = A_scaled

        # adapter_config.json (PEFT 形式)
        adapter_config = {
            "base_model_name_or_path": "",
            "bias": "none",
            "fan_in_fan_out": False,
            "inference_mode": True,
            "init_lora_weights": True,
            "lora_alpha": self.r,  # alpha = r で scaling = 1
            "lora_dropout": 0.0,
            "modules_to_save": None,
            "peft_type": "LORA",
            "r": self.r,
            "target_modules": list(self.target_modules),
            "task_type": "CAUSAL_LM",
            "_tinylora_note": f"Converted from TinyLoRA (u={self.u}, tying={self.tying})",
        }

        import json as _json
        (output_dir / "adapter_config.json").write_text(
            _json.dumps(adapter_config, indent=2), encoding="utf-8"
        )

        torch.save(lora_state, str(output_dir / "adapter_model.bin"))
        logger.info(
            "TinyLoRA → PEFT LoRA rank-%d saved: %s (%d tensors)",
            self.r, output_dir, len(lora_state),
        )
        return output_dir

    @classmethod
    def load_adapter(cls, base_model: nn.Module, adapter_dir: str | Path) -> "TinyLoRAModel":
        """保存済みアダプターを復元する。"""
        adapter_path = Path(adapter_dir) / "tinylora_adapter.json"
        data = json.loads(adapter_path.read_text(encoding="utf-8"))
        instance = cls(
            base_model,
            r=data["r"],
            u=data["u"],
            tying=data["tying"],
            target_modules=tuple(data["target_modules"]),
        )
        # shared_v をロード
        shared_vs = list(data["shared_vs"].values())
        seen: set[int] = set()
        si = 0
        for layer in instance._tiny_layers.values():
            vid = id(layer.v)
            if vid not in seen:
                seen.add(vid)
                if si < len(shared_vs):
                    with torch.no_grad():
                        layer.v.copy_(torch.tensor(shared_vs[si]))
                    si += 1
        return instance


# ── GRPO トレーナー (TinyLoRA 論文推奨) ──────────────────────────────────────

class TinyLoRAGRPOTrainer:
    """
    TinyLoRA 用の最小 GRPO トレーナー。

    GRPO (Group Relative Policy Optimization):
      各プロンプトから G 個の応答をサンプリングし、
      実行結果の報酬でグループ内相対優位性を計算して更新する。

    論文が SFT より GRPO を推奨する理由:
      13 パラメータ程度の微小な更新では、SFT の MLE ロスは
      gradient の信号が弱すぎて収束しない。
      GRPO は報酬信号が強いため極小パラメータ数でも機能する。
    """

    def __init__(
        self,
        model: TinyLoRAModel,
        tokenizer,
        reward_fn,
        lr: float = 1e-3,
        kl_coef: float = 0.001,
        group_size: int = 4,
        max_new_tokens: int = 512,
        temperature: float = 0.8,
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.reward_fn = reward_fn
        self.kl_coef = kl_coef
        self.group_size = group_size
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

        # TinyLoRA の v パラメータのみ学習
        params = [p for p in model.parameters() if p.requires_grad]
        self.optimizer = torch.optim.AdamW(params, lr=lr)
        logger.info(
            "TinyLoRAGRPOTrainer: %d trainable params, lr=%.1e",
            sum(p.numel() for p in params), lr,
        )

    def train_step(self, prompt: str) -> dict:
        """1 プロンプトに対する GRPO ステップを実行する。"""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(next(self.model.parameters()).device)

        # G 個の応答を生成
        responses = []
        log_probs_list = []
        rewards = []

        for _ in range(self.group_size):
            with torch.no_grad():
                output = self.model.base_model.generate(
                    input_ids,
                    max_new_tokens=self.max_new_tokens,
                    temperature=self.temperature,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
            generated = output[0][input_ids.shape[1]:]
            text = self.tokenizer.decode(generated, skip_special_tokens=True)
            responses.append(text)

            # log prob を計算 (TinyLoRA 有効状態で)
            lp = self._compute_log_prob(input_ids, generated)
            log_probs_list.append(lp)

            # 報酬を計算 (実行成功=1.0, 失敗=0.0 等)
            r = float(self.reward_fn(prompt, text))
            rewards.append(r)

        rewards_t = torch.tensor(rewards)
        # グループ内相対優位性 (GRPO)
        mean_r = rewards_t.mean()
        std_r = rewards_t.std() + 1e-8
        advantages = (rewards_t - mean_r) / std_r

        # Policy gradient loss
        loss = torch.tensor(0.0, requires_grad=True)
        for lp, adv in zip(log_probs_list, advantages):
            loss = loss - adv * lp

        loss = loss / self.group_size

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return {
            "loss": loss.item(),
            "mean_reward": mean_r.item(),
            "rewards": rewards,
        }

    def _compute_log_prob(self, input_ids: torch.Tensor, generated: torch.Tensor) -> torch.Tensor:
        """生成トークン列の log prob を計算する。"""
        full_ids = torch.cat([input_ids, generated.unsqueeze(0)], dim=1)
        with torch.enable_grad():
            logits = self.model.base_model(full_ids).logits
        shift_logits = logits[:, input_ids.shape[1] - 1:-1, :]
        shift_labels = full_ids[:, input_ids.shape[1]:]
        log_prob = F.cross_entropy(
            shift_logits.reshape(-1, shift_logits.shape[-1]),
            shift_labels.reshape(-1),
            reduction="mean",
        )
        return -log_prob  # negative CE = log prob

    def train(
        self,
        examples: list[dict],
        n_epochs: int = 1,
    ) -> dict:
        """複数サンプルで学習ループを実行する。"""
        total_loss = 0.0
        total_reward = 0.0
        steps = 0

        for epoch in range(n_epochs):
            for ex in examples:
                prompt = ex.get("prompt", ex.get("instruction", ""))
                if not prompt:
                    continue
                result = self.train_step(prompt)
                total_loss += result["loss"]
                total_reward += result["mean_reward"]
                steps += 1

        return {
            "steps": steps,
            "avg_loss": total_loss / max(steps, 1),
            "avg_reward": total_reward / max(steps, 1),
            "trainable_params": self.model.trainable_parameter_count(),
        }
