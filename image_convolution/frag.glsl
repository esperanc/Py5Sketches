#version 300 es
precision highp float;

in vec2 v_texCoord;
uniform sampler2D u_texture;

// The 3x3 convolution mask passed as a flat array of 9 floats
uniform float u_kernel[9];

// A weight to divide the final sum by (usually the sum of the kernel)
uniform float u_weight;

// How to treat color while convolving:
//   0 = rgb             -> convolve each channel independently (uniform)
//   1 = luminance       -> convolve only luminance, output grayscale
//   2 = luminance_color -> convolve luminance, but keep the pixel's original color
uniform int u_mode;

out vec4 fragColor;

// Rec. 709 luminance weights
const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);

void main() {
    ivec2 textureSize2d = textureSize(u_texture, 0);
    ivec2 centerCoords = ivec2(v_texCoord * vec2(textureSize2d));

    vec3 colorSum = vec3(0.0); // accumulated per-channel convolution (rgb mode)
    float lumaSum = 0.0;       // accumulated luminance convolution

    // Loop through the 3x3 neighborhood
    // i controls the x offset (-1, 0, 1), j controls the y offset (-1, 0, 1)
    int k = 0; // index for our flat kernel array
    for (int i = -1; i <= 1; i++) {
        for (int j = -1; j <= 1; j++) {

            // Calculate neighbor coordinates
            ivec2 offset = ivec2(j, i);

            // Clamp the coordinates to prevent fetching outside the texture edges
            ivec2 neighborCoords = clamp(centerCoords + offset, ivec2(0), textureSize2d - ivec2(1));

            // Fetch the pixel color
            vec3 color = texelFetch(u_texture, neighborCoords, 0).rgb;

            // Multiply by the kernel weight and add to the sums
            colorSum += color * u_kernel[k];
            lumaSum  += dot(color, LUMA) * u_kernel[k];
            k++;
        }
    }

    // Fetch the original center pixel (for alpha and color preservation)
    vec4 center = texelFetch(u_texture, centerCoords, 0);
    float alpha = center.a;

    vec3 result;
    if (u_mode == 1) {
        // Grayscale: replicate the convolved luminance across all channels
        result = vec3(lumaSum / u_weight);
    } else if (u_mode == 2) {
        // Preserve color: scale the original color so its luminance matches
        // the convolved luminance, keeping hue and saturation intact.
        float centerLuma = dot(center.rgb, LUMA);
        result = center.rgb * (lumaSum / u_weight) / max(centerLuma, 0.001);
    } else {
        // Default rgb: independent per-channel convolution
        result = colorSum / u_weight;
    }

    fragColor = vec4(result, alpha);
}