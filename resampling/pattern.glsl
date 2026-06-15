#version 300 es
precision highp float;

in vec2 v_texCoord;

// Which synthetic test pattern to generate:
//   0 = zone plate   1 = Siemens star   2 = checker   3 = chirp
uniform int u_pattern;

out vec4 fragColor;

const float PI = 3.14159265359;

// Analytic black & white pattern as a function of p in [0,1] x [0,1].
float pattern(vec2 p) {
    vec2 c = (p - 0.5) * 2.0; // centered coords in [-1, 1]

    if (u_pattern == 0) {
        // Zone plate: radial frequency grows toward the edges.
        float r2 = dot(c, c);
        return 0.5 + 0.5 * cos(24.0 * PI * r2);
    } else if (u_pattern == 1) {
        // Siemens star: angular wedges that converge (high freq) at the center.
        float ang = atan(c.y, c.x);
        return step(0.0, sin(36.0 * ang));
    } else if (u_pattern == 2) {
        // Coarse checkerboard: ideal to see nearest vs smooth interpolation.
        float f = 8.0;
        return mod(floor(p.x * f) + floor(p.y * f), 2.0);
    } else {
        // Horizontal chirp: spatial frequency increases with x.
        return 0.5 + 0.5 * cos(PI * (2.0 + 70.0 * p.x) * p.x);
    }
}

void main() {
    // Supersample so the generated source itself is band-limited (clean),
    // and the artifacts we see later come purely from the resampling step.
    vec2 dx = dFdx(v_texCoord);
    vec2 dy = dFdy(v_texCoord);

    const int S = 4;
    float sum = 0.0;
    for (int j = 0; j < S; j++) {
        for (int i = 0; i < S; i++) {
            vec2 o = (vec2(float(i), float(j)) + 0.5) / float(S) - 0.5;
            sum += pattern(v_texCoord + o.x * dx + o.y * dy);
        }
    }
    float v = sum / float(S * S);

    fragColor = vec4(vec3(v), 1.0);
}
