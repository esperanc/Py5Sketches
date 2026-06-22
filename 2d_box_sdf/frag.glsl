precision highp float;

float sdBox(vec2 p, vec2 b ) {
    vec2 d = abs(p)-b;
    return length(max(d,0.0)) + min(max(d.x,d.y),0.0);
}

vec3 color (float d) {
   	// coloring
    vec3 col = (d>0.0) ? vec3(0.9,0.6,0.3) : vec3(0.65,0.85,1.0);
    d /= 300.0;
    col *= 1.0 - exp(-6.0*abs(d));
	col *= 0.8 + 0.2*cos(150.0*d);
	return mix( col, vec3(1.0), 1.0-smoothstep(0.0,0.01,abs(d)) );;
}

void main() {
    float d = sdBox(
        gl_FragCoord.xy - vec2(400,400), 
        vec2(100,200));
    gl_FragColor = vec4(color(d),1.);
}