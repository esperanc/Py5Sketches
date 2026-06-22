precision highp float;

void main() {
    vec2 v = gl_FragCoord.xy - vec2(400.,400.);
    if (length(v)<300.0)
        gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
    else
        gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
}