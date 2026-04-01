import Lake
open Lake DSL

package «nc-kart-proof» where
  -- add package configuration options here

lean_lib «NcKartProof» where
  -- add library configuration options here

@[default_target]
lean_exe «nc-kart-proof» where
  root := `Main

require mathlib from git
  "https://github.com/leanprover-community/mathlib4"
