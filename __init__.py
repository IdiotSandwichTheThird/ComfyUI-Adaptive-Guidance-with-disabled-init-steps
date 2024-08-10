import comfy.samplers
import comfy_extras.nodes_perpneg
import torch

cos = torch.nn.CosineSimilarity(dim=1)


class Guider_AdaptiveGuidance(comfy.samplers.CFGGuider):
    threshold_timestep = 0
    uz_scale = 0.0
    initial_disabled_steps = 0
    current_step = 0

    def set_cfg(self, cfg):
        self.cfg = cfg

    def set_threshold(self, threshold):
        self.threshold = threshold

    def set_uncond_zero_scale(self, scale):
        self.uz_scale = scale

    def set_initial_disabled_steps(self, steps):
        self.initial_disabled_steps = steps

    def zero_cond(self, args):
        cond = args["cond_denoised"]
        x = args["input"]
        x -= x.mean()
        cond -= cond.mean()
        return x - (cond / cond.std() ** 0.5) * self.uz_scale

    def predict_noise(self, x, timestep, model_options={}, seed=None):
        cond = self.conds.get("positive")
        uncond = self.conds.get("negative")
        ts = timestep[0].item()
        self.current_step += 1

        if self.current_step <= self.initial_disabled_steps or self.threshold_timestep > ts:
            if self.uz_scale > 0.0:
                model_options = model_options.copy()
                model_options["sampler_cfg_function"] = self.zero_cond
            return comfy.samplers.sampling_function(
                self.inner_model, x, timestep, uncond, cond, 1.0, model_options=model_options, seed=seed
            )
        
        self.threshold_timestep = 0
        uncond_pred, cond_pred = comfy.samplers.calc_cond_batch(
            self.inner_model, [uncond, cond], x, timestep, model_options
        )
        if not self.threshold >= 1.0:
            sim = cos(cond_pred.reshape(1, -1), uncond_pred.reshape(1, -1)).item()
            if sim >= self.threshold:
                print(f"\nAdaptiveGuidance: Cosine similarity {sim:.4f} exceeds threshold, setting CFG to 1.0")
                self.threshold_timestep = ts
        return comfy.samplers.cfg_function(
            self.inner_model,
            cond_pred,
            uncond_pred,
            self.cfg,
            x,
            timestep,
            model_options=model_options,
            cond=cond,
            uncond=uncond,
        )

class AdaptiveGuidanceGuider:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "threshold": ("FLOAT", {"default": 0.990, "min": 0.90, "max": 1.0, "step": 0.001, "round": 0.001}),
                "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01}),
                "initial_disabled_steps": ("INT", {"default": 0, "min": 0, "max": 1000, "step": 1}),
            },
            "optional": {"uncond_zero_scale": ("FLOAT", {"default": 0.0, "max": 2.0, "step": 0.01})},
        }

    RETURN_TYPES = ("GUIDER",)
    FUNCTION = "get_guider"

    CATEGORY = "sampling/custom_sampling/guiders"

    def get_guider(self, model, positive, negative, threshold, cfg, initial_disabled_steps, uncond_zero_scale=0.0):
        g = Guider_AdaptiveGuidance(model)
        g.set_conds(positive, negative)
        g.set_threshold(threshold)
        g.set_uncond_zero_scale(uncond_zero_scale)
        g.set_cfg(cfg)
        g.set_initial_disabled_steps(initial_disabled_steps)

        return (g,)

class Guider_PerpNegAG(comfy_extras.nodes_perpneg.Guider_PerpNeg):
    threshold_timestep = 0
    uz_scale = 0.0
    initial_disabled_steps = 0
    current_step = 0

    def set_threshold(self, threshold):
        self.threshold = threshold

    def set_uncond_zero_scale(self, scale):
        self.uz_scale = scale

    def set_initial_disabled_steps(self, steps):
        self.initial_disabled_steps = steps

    def zero_cond(self, args):
        cond = args["cond_denoised"]
        x = args["input"]
        x -= x.mean()
        cond -= cond.mean()
        return x - (cond / cond.std() ** 0.5) * self.uz_scale

    def predict_noise(self, x, timestep, model_options={}, seed=None):
        cond = self.conds.get("positive")
        uncond = self.conds.get("negative")
        ts = timestep[0].item()
        self.current_step += 1

        if self.current_step <= self.initial_disabled_steps or self.threshold_timestep > ts:
            if self.uz_scale > 0.0:
                model_options = model_options.copy()
                model_options["sampler_cfg_function"] = self.zero_cond
            return comfy.samplers.sampling_function(
                self.inner_model, x, timestep, uncond, cond, 1.0, model_options=model_options, seed=seed
            )

        self.threshold_timestep = 0
        uncond_pred, cond_pred = comfy.samplers.calc_cond_batch(
            self.inner_model, [uncond, cond], x, timestep, model_options
        )
        if not self.threshold >= 1.0:
            # Is this reshape correct? It at least gives a scalar value...
            sim = cos(cond_pred.reshape(1, -1), uncond_pred.reshape(1, -1)).item()
            if sim >= self.threshold:
                print(f"\nAdaptiveGuidance: Cosine similarity {sim:.4f} exceeds threshold, setting CFG to 1.0")
                self.threshold_timestep = ts
        return comfy.samplers.cfg_function(
            self.inner_model,
            cond_pred,
            uncond_pred,
            self.cfg,
            x,
            timestep,
            model_options=model_options,
            cond=cond,
            uncond=uncond,
        )


class PerpNegAGGuider:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "empty_conditioning": ("CONDITIONING",),
                "threshold": ("FLOAT", {"default": 0.990, "min": 0.90, "max": 1.0, "step": 0.001, "round": 0.001}),
                "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01}),
                "neg_scale": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 100.0, "step": 0.01}),
                "initial_disabled_steps": ("INT", {"default": 0, "min": 0, "max": 1000, "step": 1}),
            },
            "optional": {"uncond_zero_scale": ("FLOAT", {"default": 0.0, "max": 2.0, "step": 0.01})},
        }

    RETURN_TYPES = ("GUIDER",)
    FUNCTION = "get_guider"

    CATEGORY = "sampling/custom_sampling/guiders"

    def get_guider(
        self, model, positive, negative, empty_conditioning, threshold, cfg, neg_scale, initial_disabled_steps, uncond_zero_scale=0.0
    ):
        g = Guider_PerpNegAG(model)
        g.set_conds(positive, negative, empty_conditioning)
        g.set_threshold(threshold)
        g.set_uncond_zero_scale(uncond_zero_scale)
        g.set_cfg(cfg, neg_scale)
        g.set_initial_disabled_steps(initial_disabled_steps)

        return (g,)
    
NODE_CLASS_MAPPINGS = {
    "AdaptiveGuidance": AdaptiveGuidanceGuider,
    "PerpNegAdaptiveGuidanceGuider": PerpNegAGGuider,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AdaptiveGuidance": "AdaptiveGuider",
    "PerpNegAdaptiveGuidanceGuider": "PerpNegAdaptiveGuider",
}
