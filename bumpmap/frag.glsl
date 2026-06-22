#version 300 es

precision highp float;

in vec2 vTexCoord;
in vec3 vNormal;
out vec4 fragColor;

uniform vec2 iResolution;
uniform float iTime;
uniform sampler2D tex; 
uniform float bumpScale; // Intensidade do efeito
uniform float texBlend; // Fator de mistura da cor da textura

// Luminosity of a color
float lum(in vec4 color) {
    return 0.299 * color.r + 0.587*color.g + 0.114 * color.b;
}

const vec3 lightDir = normalize(vec3(1)); // Luz direcional

void main() {
    vec3 N = normalize(vNormal);
    vec4 tcolor = texture(tex, vTexCoord);
    float h = lum (tcolor); // Altura do terreno

    // Obter as derivadas espaciais da posição e do UV
    vec3 dp1 = dFdx(gl_FragCoord.xyz);
    vec3 dp2 = dFdy(gl_FragCoord.xyz);
    vec2 duv1 = dFdx(vTexCoord);
    vec2 duv2 = dFdy(vTexCoord);

    // Calcular Tangente (T) e Bitangente (B) no espaço do mundo
    // Usamos o produto vetorial para garantir que T e B estejam no plano da face
    vec3 dp2perp = cross(dp2, N);
    vec3 dp1perp = cross(N, dp1);
    vec3 T = normalize(dp2perp * duv1.x + dp1perp * duv2.x);
    vec3 B = normalize(dp2perp * duv1.y + dp1perp * duv2.y);

    // Calcular o gradiente da altura (como h muda em X e Y na tela)
    float dhx = dFdx(h);
    float dhy = dFdy(h);

    // Calcular a perturbação
    // Resolvemos a variação de h em relação a U e V usando as derivadas de tela
    // Mas uma forma simplificada e eficiente é:
    vec3 grad = T * dhx + B * dhy;
    
    // A nova normal é a original "puxada" pelo gradiente da altura
    vec3 bumpedNormal = normalize(N - grad * bumpScale);
    
    // grayscale texture
    // fragColor = vec4(vec3(h), 1.);
    
    // Iluminacao Difusa
    float diffuse = dot(bumpedNormal,normalize(lightDir));
    fragColor = vec4 (vec3(diffuse),1.) * mix(vec4(1), tcolor, texBlend);
    
}