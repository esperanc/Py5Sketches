precision highp float;

uniform vec2 iResolution;
uniform float iTime;

uniform vec3 oper; // Boolean operation encoding
uniform vec3 rblend; // Reflection color blending

const int MAX_MARCHING_STEPS = 255;
const float MAX_DIST = 100.0;
const float EPSILON = 0.0001;

uniform vec3 eye; // Position of the eye
const vec3 center = vec3(0., 0., 0.); // Center of scene
const vec3 up = vec3 (0., 1., 0.); // World up vector
const float flen = 1.0;   // Focus (dist from proj plane to eye)

uniform samplerCube uCubemap; // cubemap texture

float sphereSDF(vec3 p, float r) {
    return length(p) - r;
}

float blockSDF(vec3 p, vec3 sz) {
  vec3 q = abs(p) - sz;
  return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0);
}

float sceneSDF(vec3 p) {
    return oper.x * min( 
        oper.y * blockSDF(p, vec3 (0.3, 1.1, 1.1)), 
        oper.z * sphereSDF(p, 1.));
}

vec3 normal(vec3 p) {
    float d = sceneSDF(p);
    vec2 e = vec2(0., 0.01);
    return normalize(vec3(d)-
                    vec3(sceneSDF(p-e.yxx),
                         sceneSDF(p-e.xyx),
                         sceneSDF(p-e.xxy)));
}

const vec3 lightPos = vec3(10);  // Light position
const vec3 lightColor = vec3 (1); // Light color
const vec3 matColor = vec3 (1,0,0); // material Color
const float matDiff = 0.8; // Diffuse coefficient
const float matAmb = 0.3; // Ambient coefficient
const float matSpec = 0.8; // Specular coefficient
const float matShine = 20.0; // Shininess power

vec3 lighting (vec3 p) {
    vec3 n = normal(p);
    vec3 l = normalize(lightPos - p);
    vec3 e = normalize(eye - p);
    vec3 ia = matAmb * lightColor * matColor;
    vec3 id = matDiff * max(0.,dot(l, n)) * lightColor * matColor;
    vec3 r = reflect(-l,n);
    vec3 is = matSpec * pow(max(0., dot(e,r)),matShine) * lightColor;
    vec3 R = reflect(-e,n);
    vec3 T = textureCube(uCubemap, R).rgb;
    vec3 C = (ia+id+is);
    return T * rblend.x + C*rblend.y + T*C*rblend.z;
}

float rayMarch (vec3 dir) {
  float depth = 0.;
  for (int i = 0; i < MAX_MARCHING_STEPS; i++) {
    float dist = sceneSDF(eye + depth * dir);
    if (dist < EPSILON) return depth;
    depth += dist;
    if (depth >= MAX_DIST) return MAX_DIST;
  }
  return MAX_DIST;
}

vec3 rayDirection(vec2 fragCoord) {
    
  vec2 uv = fragCoord.xy / iResolution.xy - 0.5 ; // Normalized coordinates
  uv.x *= iResolution.x / iResolution.y; // Aspect ratio

  vec3 Z = normalize(eye-center); // Vector center-eye
  vec3 X = normalize(cross(up,Z));  // Vector to right of proj plane
  vec3 Y = normalize(cross(Z,X));  // Vector to top of proj plane
  vec3 C = eye - flen*Z; // Center of projection plane
  vec3 P = C + X*uv.x + Y*uv.y; // Point on proj plane
  return normalize (P - eye);
}

void main( )
{
  vec3 dir = rayDirection(gl_FragCoord.xy);
  vec3 color = textureCube(uCubemap, dir).rgb;
  float dist = rayMarch(dir);
  float hit = step(dist, MAX_DIST - EPSILON);
  vec3 p = eye+dist*dir;
  gl_FragColor = vec4(hit*lighting(p)+(1.-hit)*color, 1.0);
}