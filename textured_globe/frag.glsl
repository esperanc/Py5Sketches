#version 300 es

precision highp float;
in vec2 vTexCoord;
out vec4 fragColor;
uniform vec2 iResolution;
uniform float iTime;
uniform sampler2D tex;

void main() {
    vec2 st = gl_FragCoord.xy/iResolution.xy;
    vec4 color = texture(tex,vTexCoord);
    fragColor = color;
}
