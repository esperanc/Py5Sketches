#version 300 es

precision highp float;
out vec4 fragColor;
uniform vec2 iResolution;
uniform float iTime;
uniform sampler2D tex1;
uniform sampler2D tex2;

void main() {
    vec2 st = gl_FragCoord.xy/iResolution.xy;
    vec4 c1 = texture(tex1,vec2(st.s,1.-st.t));
    vec4 c2 = texture(tex2,vec2(st.s,1.-st.t));
    float alpha = fract(iTime/4.)*2.;
    if (alpha>1.) alpha = 2.-alpha;
    fragColor =  c1 * alpha +  c2 * (1.-alpha);
}
