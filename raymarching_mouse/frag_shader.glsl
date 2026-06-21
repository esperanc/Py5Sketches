precision highp float;

uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

const int MAX_MARCHING_STEPS = 255;
const float MAX_DIST = 100.0;
const float EPSILON = 0.0001;

const vec3 defEye = vec3(0,0, 10); // Default eye position
const vec3 center = vec3(0., 0., 0.); // Center of scene
const vec3 up = vec3 (0., 1., 0.); // World up vector
const float flen = 2.0;   // Focus (dist from proj plane to eye)

mat2 rot2d (float angle) {
    float c = cos(angle), s=sin(angle);
    return mat2(c, -s, s, c);
}

vec3 getEye () {
    vec2 m = iMouse.xy/iResolution.xy*2.-1.; // range [-1,1]
    vec3 eye = defEye;
    eye.yz *= rot2d(-m.y*3.1416/2.);
    eye.xz *= rot2d(m.x*3.1416);
    return eye;
}

float sphereSDF(vec3 p, float r) {
    return length(p) - r;
}

float blockSDF(vec3 p, vec3 sz) {
  vec3 q = abs(p) - sz;
  return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0);
}

float sceneSDF(vec3 p) {
    return blockSDF(p, vec3(1));
}

float rayMarch (vec3 eye, vec3 dir) {
  float depth = 0.;
  for (int i = 0; i < MAX_MARCHING_STEPS; i++) {
    float dist = sceneSDF(eye + depth * dir);
    if (dist < EPSILON) return depth;
    depth += dist;
    if (depth >= MAX_DIST) return MAX_DIST;
  }
  return MAX_DIST;
}

vec3 rayDirection(vec3 eye, vec2 fragCoord) {
    
    vec2 uv = fragCoord.xy / iResolution.xy - 0.5 ; // Normalized coordinates
    uv.x *= iResolution.x / iResolution.y; // Aspect ratio
    
    vec3 z_E = normalize(eye-center); // Vector center-eye
    vec3 x_E = normalize(cross(up,z_E));  // Vector to right of proj plane
    vec3 y_E = normalize(cross(z_E,x_E));  // Vector to top of proj plane
    vec3 C = eye - flen*z_E; // Center of projection plane
    vec3 P = C + x_E*uv.x + y_E*uv.y; // Point on proj plane
    return normalize (P - eye);
}

void main( )
{
    vec3 eye = getEye();
    vec3 dir = rayDirection(eye, gl_FragCoord.xy);
    float dist = rayMarch(eye, dir);
    float hit = step(dist, MAX_DIST - EPSILON);
    gl_FragColor = vec4(hit, 0.0, 0.0, 1.0);
}