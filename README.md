# Adaptive Guidance for ComfyUI with disabled CFG for initial steps


Just a quick and dirty fork of https://github.com/asagi4/ComfyUI-Adaptive-Guidance to enable very trained Flux-dev loras to work properly. I think if you train them too hard, they essentially un-distill the model, so you need to introduce CFG back into your inference. But using CFG quickly fries the image. So to avoid having to do dynamic thresholding, which results in reduced output quality, you can now skip applying cfg to the first few steps.

I recommend skipping 2-6 initial steps. Experiment and have fun.

![A very important message I am sorry if you are blind and can not read it.](https://i.redd.it/9iuntj1goca91.jpg)

## What

There's an `AdaptiveGuidance` node (under `sampling/custom_sampling/guiders`) that can be used with `SamplerCustomAdvanced`. Normally, you should keep the threshold quite high, between `0.99` and `1.0`

The node calculates the cosine similarity between the u-net's conditional and unconditional output ("positive" and "negative" prompts) and once the similarity crosses the specified threshold, it sets CFG to 1.0, effectively skipping negative prompt calculations and speeding up inference.

I'm not sure if the cosine similarity calculation matches the original paper since I had to translate from maths to Python, but it appears to work.

### Uncond zero

Set uncond_zero_scale to > 0 to enable "uncond zero" CFG *after* the normal CFG gets disabled. Stolen from https://github.com/Extraltodeus/Uncond-Zero-for-ComfyUI

It seems to work slightly better than just running without CFG, but YMMV

Note: this functionality is unstable and will probably change, so using it means your workflows likely won't be perfectly reproducible.
