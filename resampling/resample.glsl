#version 300 es
precision highp float;

in vec2 v_texCoord;

uniform sampler2D u_src;   // source image (grayscale stored in .r)
uniform int u_method;      // 0 = nearest, 1 = bilinear, 2 = bicubic (upsampling)
uniform int u_op;          // 0 = upsample (reconstruct), 1 = downsample
uniform int u_prefilter;   // 0/1 box pre-filter (downsampling only)
uniform float u_gridN;     // target grid resolution (downsampling)

out vec4 fragColor;

// Clamped texel fetch of the red channel.
float texelR(ivec2 c) {
    ivec2 sz = textureSize(u_src, 0);
    c = clamp(c, ivec2(0), sz - ivec2(1));
    return texelFetch(u_src, c, 0).r;
}

// Catmull-Rom cubic kernel.
float cubic(float x) {
    x = abs(x);
    if (x < 1.0)      return (1.5 * x - 2.5) * x * x + 1.0;
    else if (x < 2.0) return ((-0.5 * x + 2.5) * x - 4.0) * x + 2.0;
    return 0.0;
}

// Nearest-neighbour read at a continuous source uv (used while downsampling).
float srcNearest(vec2 uv) {
    vec2 sz = vec2(textureSize(u_src, 0));
    return texelR(ivec2(floor(uv * sz)));
}

// Reconstruct the source value at a continuous uv using the chosen method.
// (Texel centers sit at integer indices: p = uv * size - 0.5.)
float reconstruct(vec2 uv) {
    vec2 sz = vec2(textureSize(u_src, 0));
    vec2 p = uv * sz - 0.5;

    if (u_method == 0) {
        // Nearest neighbour: blocky.
        return texelR(ivec2(floor(p + 0.5)));
    } else if (u_method == 1) {
        // Bilinear: weighted average of the 4 surrounding texels.
        ivec2 b = ivec2(floor(p));
        vec2 f = p - vec2(b);
        float c00 = texelR(b + ivec2(0, 0));
        float c10 = texelR(b + ivec2(1, 0));
        float c01 = texelR(b + ivec2(0, 1));
        float c11 = texelR(b + ivec2(1, 1));
        return mix(mix(c00, c10, f.x), mix(c01, c11, f.x), f.y);
    } else {
        // Bicubic: 16 texels, smoother result.
        ivec2 b = ivec2(floor(p));
        vec2 f = p - vec2(b);
        float sum = 0.0;
        float wsum = 0.0;
        for (int m = -1; m <= 2; m++) {
            float wy = cubic(f.y - float(m));
            for (int n = -1; n <= 2; n++) {
                float w = cubic(f.x - float(n)) * wy;
                sum  += texelR(b + ivec2(n, m)) * w;
                wsum += w;
            }
        }
        return sum / wsum;
    }
}

void main() {
    float v;

    if (u_op == 0) {
        // UPSAMPLING: estimate values between the source samples.
        v = reconstruct(v_texCoord);
    } else {
        // DOWNSAMPLING: quantize to a coarse grid; value is constant per cell.
        vec2 cell = floor(v_texCoord * u_gridN);

        if (u_prefilter == 0) {
            // No pre-filter: point-sample the cell center -> aliasing.
            vec2 center = (cell + 0.5) / u_gridN;
            v = srcNearest(center);
        } else {
            // Box pre-filter: average the source over the cell footprint.
            float fp = vec2(textureSize(u_src, 0)).x / u_gridN; // footprint in texels
            int n = int(clamp(ceil(fp), 1.0, 10.0));
            float inv = 1.0 / float(n);
            float sum = 0.0;
            for (int j = 0; j < n; j++) {
                for (int i = 0; i < n; i++) {
                    vec2 uv = (cell + (vec2(float(i), float(j)) + 0.5) * inv) / u_gridN;
                    sum += srcNearest(uv);
                }
            }
            v = sum / float(n * n);
        }
    }

    fragColor = vec4(vec3(v), 1.0);
}
