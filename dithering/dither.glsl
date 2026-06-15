#version 300 es
precision highp float;

in vec2 v_texCoord;

uniform int u_source;    // 0 = gray ramp, 1 = color, 2 = radial (synthetic sources)
uniform int u_useImage;  // 1 = sample u_image instead of the synthetic source
uniform sampler2D u_image;
uniform int u_method;    // 0 = none, 1 = ordered 4x4, 2 = ordered 16x16, 3 = blue noise, 4 = IGN
uniform int u_mode;      // 0 = rgb, 1 = luminance
uniform float u_levels;  // output levels per channel (>= 2)

uniform sampler2D u_blue; // blue-noise tile (grayscale in .r)
uniform float u_blueSize; // size of the blue-noise tile in texels
uniform float u_frame;    // frame counter for temporal animation (0 = static)

out vec4 fragColor;

const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);

// Procedural source — MUST match source_rgb() in sketch.py.
vec3 source(vec2 uv) {
    if (u_source == 0) {
        return vec3(uv.x);
    } else if (u_source == 1) {
        return vec3(uv.x, uv.y, (uv.x + uv.y) * 0.5);
    } else {
        float d = clamp(length(uv - 0.5) * 2.0, 0.0, 1.0);
        return vec3(1.0 - d);
    }
}

// Recursive Bayer ordered-dither matrices, value in [0,1).
float bayer2(vec2 a)  { a = floor(a); return fract(a.x * 0.5 + a.y * a.y * 0.75); }
float bayer4(vec2 a)  { return bayer2(0.5 * a) * 0.25 + bayer2(a); }
float bayer8(vec2 a)  { return bayer4(0.5 * a) * 0.25 + bayer2(a); }
float bayer16(vec2 a) { return bayer8(0.5 * a) * 0.25 + bayer2(a); }

// Blue-noise threshold: a tileable blue-noise texture (energy in the high
// frequencies, no low-frequency clumping). For temporal blue noise we shift
// the value by the golden ratio each frame (Wronski) — stays blue over time.
float blueNoise(vec2 fc) {
    ivec2 c = ivec2(mod(fc, u_blueSize));
    float t = texelFetch(u_blue, c, 0).r;
    return fract(t + u_frame * 0.61803399);
}

// Interleaved Gradient Noise (Jorge Jimenez, Call of Duty). Analytic, no
// texture, cheap, quality close to blue noise. Animated by offsetting coords.
float ign(vec2 fc) {
    vec2 p = fc + u_frame * 5.588238;
    return fract(52.9829189 * fract(0.06711056 * p.x + 0.00583715 * p.y));
}

// Quantize one channel to u_levels using a dither threshold t in [0,1).
float ditherChannel(float v, float t) {
    float L = u_levels;
    float scaled = v * (L - 1.0);
    float lower = floor(scaled);
    float frac = scaled - lower;
    float level = lower + step(t, frac);   // bump up if fractional part beats threshold
    return clamp(level, 0.0, L - 1.0) / (L - 1.0);
}

void main() {
    vec3 col = (u_useImage == 1)
        ? texture(u_image, v_texCoord).rgb
        : source(v_texCoord);

    if (u_method == 0) {
        // Original (no dithering, no quantization) — reference for the banding.
        fragColor = vec4(col, 1.0);
        return;
    }

    float t;
    if (u_method == 1)      t = bayer4(gl_FragCoord.xy);
    else if (u_method == 2) t = bayer16(gl_FragCoord.xy);
    else if (u_method == 3) t = blueNoise(gl_FragCoord.xy);
    else                    t = ign(gl_FragCoord.xy);

    vec3 outc;
    if (u_mode == 1) {
        // Luminance: dither a single intensity channel -> grayscale output.
        float d = ditherChannel(dot(col, LUMA), t);
        outc = vec3(d);
    } else {
        // RGB: dither each channel independently.
        outc = vec3(ditherChannel(col.r, t),
                    ditherChannel(col.g, t),
                    ditherChannel(col.b, t));
    }

    fragColor = vec4(outc, 1.0);
}
