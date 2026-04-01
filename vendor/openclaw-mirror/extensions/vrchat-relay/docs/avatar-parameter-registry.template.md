## Avatar Parameter Registry Template

Use this table before enabling autonomous reactions. Keep parameter names exactly identical to Unity Expression Parameters.

| Purpose       | Parameter    | Type | Default | Trigger Source                      |
| ------------- | ------------ | ---- | ------- | ----------------------------------- |
| Smile         | FX_Smile     | bool | false   | `vrchat_autonomy_react` (joy)       |
| Love          | FX_Love      | bool | false   | `vrchat_autonomy_react` (love)      |
| Angry         | FX_Angry     | bool | false   | `vrchat_autonomy_react` (angry)     |
| Sad           | FX_Sad       | bool | false   | `vrchat_autonomy_react` (sad)       |
| Surprise      | FX_Surprised | bool | false   | `vrchat_autonomy_react` (surprised) |
| Generic Emote | VRCEmote     | int  | 0       | Ghost Bridge / Guardian Pulse       |

### Animator Notes

- Add transitions from neutral to each `FX_*` state using bool conditions.
- Add return transitions to neutral when parameter returns to `false`.
- Keep transition duration short (`0.05` to `0.15`) for responsive reactions.
- If using blend trees, avoid writing the same parameter from multiple animator layers.
