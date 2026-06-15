#version 300 es
precision highp float;

in vec2 v_texCoord;

uniform sampler2D u_tex0;
uniform sampler2D u_tex1;

uniform int u_pass;       // qual operacao executar (ver constantes abaixo)
uniform float u_kernel[9];
uniform float u_div;
uniform float u_bias;
uniform int u_gray;       // CONV3: 1 = converte saida para tons de cinza
uniform vec2 u_dir;       // BLUR1D: direcao em texels (1,0) ou (0,1)
uniform float u_sigma;
uniform int u_radius;
uniform int u_op;         // GRADMAG: 0 = Sobel, 1 = Prewitt
uniform float u_scale;    // ganho de magnitude (sensibilidade de borda)
uniform float u_a, u_b, u_c;  // COMBINE: a*tex0 + b*tex1 + c
uniform float u_hi, u_lo;     // THRESH: limiares alto/baixo

out vec4 fragColor;

const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);
const float PI = 3.14159265359;

// Constantes de passada (espelham PASS_* em sketch.py)
const int COPY = 0, GRAY = 1, CONV3 = 2, BLUR1D = 3, GRADMAG = 4,
          MAGVIEW = 5, NMS = 6, THRESH = 7, HYST = 8, FINALIZE = 9, COMBINE = 10;

ivec2 SZ0;
ivec2 C0;
ivec2 SZ1;
ivec2 C1;

vec4 fetch0(ivec2 o) {
    return texelFetch(u_tex0, clamp(C0 + o, ivec2(0), SZ0 - ivec2(1)), 0);
}
vec4 fetch1(ivec2 o) {
    return texelFetch(u_tex1, clamp(C1 + o, ivec2(0), SZ1 - ivec2(1)), 0);
}
float lum(ivec2 o) { return dot(fetch0(o).rgb, LUMA); }

void gradient(out float gx, out float gy) {
    float k = (u_op == 0) ? 2.0 : 1.0;  // Sobel usa peso 2 no centro; Prewitt usa 1
    float tl = lum(ivec2(-1, -1)), t = lum(ivec2(0, -1)), tr = lum(ivec2(1, -1));
    float ml = lum(ivec2(-1, 0)),                         mr = lum(ivec2(1, 0));
    float bl = lum(ivec2(-1, 1)), b = lum(ivec2(0, 1)), br = lum(ivec2(1, 1));
    gx = (tr + k * mr + br) - (tl + k * ml + bl);
    gy = (bl + k * b + br) - (tl + k * t + tr);
}

void main() {
    SZ0 = textureSize(u_tex0, 0);
    C0 = ivec2(v_texCoord * vec2(SZ0));
    SZ1 = textureSize(u_tex1, 0);
    C1 = ivec2(v_texCoord * vec2(SZ1));

    vec3 o = vec3(0.0);

    if (u_pass == COPY) {
        o = fetch0(ivec2(0)).rgb;

    } else if (u_pass == GRAY) {
        o = vec3(lum(ivec2(0)));

    } else if (u_pass == CONV3) {
        vec3 s = vec3(0.0);
        int idx = 0;
        for (int j = -1; j <= 1; j++)
            for (int i = -1; i <= 1; i++)
                s += u_kernel[idx++] * fetch0(ivec2(i, j)).rgb;
        o = s / u_div + u_bias;
        if (u_gray == 1) o = vec3(dot(o, LUMA));

    } else if (u_pass == BLUR1D) {
        vec3 acc = vec3(0.0);
        float wsum = 0.0;
        for (int i = -u_radius; i <= u_radius; i++) {
            float w = exp(-0.5 * float(i * i) / (u_sigma * u_sigma));
            acc += w * fetch0(ivec2(u_dir) * i).rgb;
            wsum += w;
        }
        o = acc / wsum;

    } else if (u_pass == GRADMAG) {
        float gx, gy;
        gradient(gx, gy);
        float mag = length(vec2(gx, gy)) * u_scale;
        // empacota: r,g = gradiente (com bias), b = magnitude (para Sobel/Canny)
        o = vec3(gx / 8.0 + 0.5, gy / 8.0 + 0.5, clamp(mag, 0.0, 1.0));

    } else if (u_pass == MAGVIEW) {
        o = vec3(fetch0(ivec2(0)).b);  // mostra a magnitude empacotada

    } else if (u_pass == NMS) {
        // supressao nao-maxima: mantem o pixel so se for maximo local na
        // direcao do gradiente.
        vec4 c = fetch0(ivec2(0));
        float gx = (c.r - 0.5) * 8.0;
        float gy = (c.g - 0.5) * 8.0;
        float m = c.b;
        float ang = mod(atan(gy, gx) + PI, PI);  // 0..pi
        ivec2 d;
        if (ang < PI / 8.0 || ang >= 7.0 * PI / 8.0) d = ivec2(1, 0);
        else if (ang < 3.0 * PI / 8.0) d = ivec2(1, 1);
        else if (ang < 5.0 * PI / 8.0) d = ivec2(0, 1);
        else d = ivec2(-1, 1);
        float m1 = fetch0(d).b;
        float m2 = fetch0(-d).b;
        o = (m >= m1 && m >= m2) ? vec3(m) : vec3(0.0);

    } else if (u_pass == THRESH) {
        // duplo limiar: forte = 1.0, fraco = 0.5, nenhum = 0.0
        float m = fetch0(ivec2(0)).r;
        o = (m >= u_hi) ? vec3(1.0) : (m >= u_lo ? vec3(0.5) : vec3(0.0));

    } else if (u_pass == HYST) {
        // histerese: promove um pixel fraco a forte se vizinho for forte
        float v = fetch0(ivec2(0)).r;
        if (v >= 0.99) {
            o = vec3(1.0);
        } else if (v >= 0.25) {
            float mx = 0.0;
            for (int j = -1; j <= 1; j++)
                for (int i = -1; i <= 1; i++)
                    mx = max(mx, fetch0(ivec2(i, j)).r);
            o = (mx >= 0.99) ? vec3(1.0) : vec3(0.5);
        } else {
            o = vec3(0.0);
        }

    } else if (u_pass == FINALIZE) {
        o = (fetch0(ivec2(0)).r >= 0.99) ? vec3(1.0) : vec3(0.0);

    } else if (u_pass == COMBINE) {
        o = u_a * fetch0(ivec2(0)).rgb + u_b * fetch1(ivec2(0)).rgb + u_c;
    }

    fragColor = vec4(clamp(o, 0.0, 1.0), 1.0);
}
