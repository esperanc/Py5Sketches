#version 300 es

precision highp float;

// Declare an output variable for the fragment color (required in GLSL ES 3.00)
out vec4 fragColor;

// From https://www.shadertoy.com/view/Xs3fR4
// variant of "Vorocracks marble" https://shadertoy.com/view/Xs3fR4
// variant of Vorocracks: https://shadertoy.com/view/lsVyRy

#define MM 0
#define DEMO 1
#define MARBLE 1

#if MARBLE==0            // simple cracks

#  define VARIANT 0            // 1: amplifies Voronoi cell jittering
float CELL = 8.,               // cells tiling
      RATIO = 2.,              // stone length/width ratio
      STONE_slope = .3,        // 0.  .3 
      STONE_height = 1.,       // 1.  1. 
      profile = 1.,            // z = height + slope * dist ^ prof
   
      fractal_depth = 1.,      // multiscale cracks
      fractal_scale = 2.5,
      noise_scale = .67,       // fractal shape of the fault zebra
      noise_amp = .59,
      BEVEL = 10.,             // cracks profile = \_ = bevel,width
      GAP = .0;

#else                    // marble

#  define VARIANT 1            // 1: amplifies Voronoi cell jittering
float CELL = 4.,               // cells tiling
      RATIO = 1.,              // stone length/width ratio
   
      fractal_depth = 3.,      // multiscale cracks
      fractal_scale = 1.5,
      noise_scale = 1.,        // fractal shape of the fault zebra
      noise_amp = .67,
      BEVEL = 50.,             // cracks profile = \_ = bevel,width       
      GAP = .0;
#endif


#if VARIANT
      float ofs = .5;          // jitter Voronoi centers in -ofs ... 1.+ofs
#else
      float ofs = 0.;
#endif
        

// std int hash, inspired from https://www.shadertoy.com/view/XlXcW4
vec3 hash3( uvec3 x ) 
{
#   define scramble  x = ( (x>>8U) ^ x.yzx ) * 1103515245U // GLIB-C const
    scramble; scramble; scramble; 
    return vec3(x) / float(0xffffffffU) + 1e-30; // <- eps to fix a windows/angle bug
}

// === Voronoi =====================================================
// --- Base Voronoi. inspired by https://www.shadertoy.com/view/MslGD8

#define hash22(p)  fract( 18.5453 * sin( p * mat2(127.1,311.7,269.5,183.3)) )
#define disp(p) ( -ofs + (1.+2.*ofs) * hash22(p) )

vec3 voronoi( vec2 u )  // returns len + id
{
    vec2 iu = floor(u), v;
	float m = 1e9,d;
#if VARIANT
    for( int k=0; k < 25; k++ ) {
        vec2  p = iu + vec2(k%5-2,k/5-2),
#else
    for( int k=0; k < 9; k++ ) {
        vec2  p = iu + vec2(k%3-1,k/3-1),
#endif
            o = disp(p),
      	      r = p - u + o;
		d = dot(r,r);
        if( d < m ) m = d, v = r;
    }

    return vec3( sqrt(m), v+u );
}

// --- Voronoi distance to borders. inspired by https://www.shadertoy.com/view/ldl3W8
vec3 voronoiB( vec2 u )  // returns len + id
{
    vec2 iu = floor(u), C, P;
	float m = 1e9,d;
#if VARIANT
    for( int k=0; k < 25; k++ ) {
        vec2  p = iu + vec2(k%5-2,k/5-2),
#else
    for( int k=0; k < 9; k++ ) {
        vec2  p = iu + vec2(k%3-1,k/3-1),
#endif
              o = disp(p),
      	      r = p - u + o;
		d = dot(r,r);
        if( d < m ) m = d, C = p-iu, P = r;
    }

    m = 1e9;
    
    for( int k=0; k < 25; k++ ) {
        vec2 p = iu+C + vec2(k%5-2,k/5-2),
		     o = disp(p),
             r = p-u + o;

        if( dot(P-r,P-r)>1e-5 )
        m = min( m, .5*dot( (P+r), normalize(r-P) ) );
    }

    return vec3( m, P+u );
}

// === pseudo Perlin noise =============================================
#define rot(a) mat2(cos(a),-sin(a),sin(a),cos(a))
int MOD = 1;  // type of Perlin noise
    
// --- 2D
#define hash21(p) fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123)
float noise2(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p); f = f*f*(3.-2.*f); // smoothstep

    float v= mix( mix(hash21(i+vec2(0,0)),hash21(i+vec2(1,0)),f.x),
                  mix(hash21(i+vec2(0,1)),hash21(i+vec2(1,1)),f.x), f.y);
	return   MOD==0 ? v
	       : MOD==1 ? 2.*v-1.
           : MOD==2 ? abs(2.*v-1.)
                    : 1.-abs(2.*v-1.);
}

float fbm2(vec2 p) {
    float v = 0.,  a = .5;
    mat2 R = rot(.37);

    for (int i = 0; i < 9; i++, p*=2.,a/=2.) 
        p *= R,
        v += a * noise2(p);

    return v;
}
#define noise22(p) vec2(noise2(p),noise2(p+17.7))
vec2 fbm22(vec2 p) {
    vec2 v = vec2(0);
    float a = .5;
    mat2 R = rot(.37);

    for (int i = 0; i < 6; i++, p*=2.,a/=2.) 
        p *= R,
        v += a * noise22(p);

    return v;
}
vec2 mfbm22(vec2 p) {  // multifractal fbm 
    vec2 v = vec2(1);
    float a = .5;
    mat2 R = rot(.37);

    for (int i = 0; i < 6; i++, p*=2.,a/=2.) 
        p *= R,
        //v *= 1.+noise22(p);
          v += v * a * noise22(p);

    return v-1.;
}

/*
// --- 3D 
#define hash31(p) fract(sin(dot(p,vec3(127.1,311.7, 74.7)))*43758.5453123)
float noise3(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p); f = f*f*(3.-2.*f); // smoothstep

    float v= mix( mix( mix(hash31(i+vec3(0,0,0)),hash31(i+vec3(1,0,0)),f.x),
                       mix(hash31(i+vec3(0,1,0)),hash31(i+vec3(1,1,0)),f.x), f.y), 
                  mix( mix(hash31(i+vec3(0,0,1)),hash31(i+vec3(1,0,1)),f.x),
                       mix(hash31(i+vec3(0,1,1)),hash31(i+vec3(1,1,1)),f.x), f.y), f.z);
	return   MOD==0 ? v
	       : MOD==1 ? 2.*v-1.
           : MOD==2 ? abs(2.*v-1.)
                    : 1.-abs(2.*v-1.);
}

float fbm3(vec3 p) {
    float v = 0.,  a = .5;
    mat2 R = rot(.37);

    for (int i = 0; i < 9; i++, p*=2.,a/=2.) 
        p.xy *= R, p.yz *= R,
        v += a * noise3(p);

    return v;
}
*/
    
// ======================================================

uniform vec2 iResolution;
uniform float iTime;

void main()
{
    vec2 U = gl_FragCoord.xy;
    vec4 O = vec4(0.);
    U *= CELL/iResolution.y;
#if DEMO
    U.x += iTime;                                     // for demo
 // O = vec4( 1.-voronoiB(U).x,voronoi(U).x, 0,0 );   // for tests
    vec2 I = floor(U/2.); 
    bool vert = mod(I.x+I.y,2.)==1.; //if (vert) U = U.yx;
#endif
    vec3 H0;
    O-=O;

    for(float i=0.; i<fractal_depth ; i++) {
        vec2 V =  U / vec2(RATIO,1),                  // voronoi cell shape
             D = noise_amp * fbm22(U/noise_scale) * noise_scale;
        vec3  H = voronoiB( V + D ); if (i==0.) H0=H;
        float d = H.x;                                // distance to cracks
        d = clamp( BEVEL * (d-GAP) ,0., 1.);

#if MARBLE==0        
        float r = voronoi(V).x,                       // distance to center
              s = STONE_height-STONE_slope*pow(r,profile);  // stone interior
        d *= s;                                       // fault * stone
#endif       
        O += vec4(1.-d) / exp2(i);  // NB: if no fractal we just have O = d
        U *= fractal_scale * rot(.37);
    }
    
    O = 1.-O;
#if DEMO&&MARBLE
    if (vert) O = 1.-O; O *= vec4(.9,.85,.85,1);      // for demo
#endif
    
#if MM
    O.g = hash3(uvec3(H0.yz,1)).x;
#endif
    fragColor = O;
}