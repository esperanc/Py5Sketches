#version 300 es

precision highp float;
out vec4 fragColor;
uniform vec2 iResolution;
uniform float iTime;
// From https://www.shadertoy.com/view/wsBXDt

/*

	Random Tiled Pattern
	--------------------

	Creating a distance field value for a random tiled pattern, then applying standard image 
	software layering techniques to produce a raised-looking hand drawn image.

	I used to love playing around with Photoshop, but haven't used it since Adobe moved to the 
    subscription model, which the 90s internet user in me isn't comfortable with. Regardless, 
	I still like to apply Photoshop layering principles in Shadertoy.

	Most of the techniques used in this example employ common sense: Create a 2D vector field, 
    then render various layers over the top of one another. For instance, a black field shape 
	followed by a slightly thinner colored one will give the appearance of a colored vector 
	image with a dark stroke line, and so forth. Render a faded shape with an offset position 
	onto the background prior to rendering the other layers, and you have yourself a shadow, 
	etc.
	
	The pattern itself is nothing special, but I like the way it looks. The most common square
	Truchet tile consists of a couple of arc lines. This one is constructed via a few more arc 
	lines in each tile, whilst still maintaining rotational symmetry. You can see a similar 
	example in the paper "Truchet Tiles Revisited," which I've provided a link to below. 
	However, uncommenting the "SHOW_GRID" define should give you a fair idea.

 	I went for a kind of grungey hand drawn style... Probably not to everyone's taste, but with 
	a bit of imagination, all kinds of styles are possible. Just for fun, and to keep Dr2 happy, 
	I produced my own texture, which is just a mixture of noise and color. I coded this in the 
	800 by 450 window on a 17 inch laptop, but have tried to keep it looking similar in other 
	screen settings.



	Pattern based on an image in the following paper:

	Truchet Tiles Revisited - Robert J. Krawczyk
	http://mypages.iit.edu/~krawczyk/rjkisama11.pdf




*/

// Show the square grid markings, which enables the viewer to see the individual tiles.
//#define SHOW_GRID


// Shorthand.
#define sstep(sf, d) (1. - smoothstep(0., sf, d))


// Standard 2D rotation formula.
mat2 rot2(in float a){ float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }


// IQ's standard vec2 to float hash formula.
float hash21(vec2 p){
 
    float n = dot(p, vec2(127.183, 157.927));
    return fract(sin(n)*43758.5453);
}


// Cheap and nasty 2D smooth noise function with inbuilt hash function -- based on IQ's 
// original. Very trimmed down. In fact, I probably went a little overboard. I think it 
// might also degrade with large time values.
float n2D(vec2 p) {

	vec2 i = floor(p); p -= i; p *= p*(3. - p*2.);  
    
	return dot(mat2(fract(sin(vec4(0, 1, 113, 114) + dot(i, vec2(1, 113)))*43758.5453))*
                vec2(1. - p.y, p.y), vec2(1. - p.x, p.x) );

}

// FBM -- 4 accumulated noise layers of modulated amplitudes and frequencies.
float fbm(vec2 p){ return n2D(p)*.533 + n2D(p*2.)*.267 + n2D(p*4.)*.133 + n2D(p*8.)*.067; }


// Distance field for the grid tile.
float TilePattern(vec2 p){
    
     
    vec2 ip = floor(p); // Cell ID.
    p -= ip + .5; // Cell's local position. Range [vec2(-.5), vec2(.5)].
    
     
    // Using the cell ID to generate a unique random number.
    float rnd = hash21(ip);
    float rnd2 = hash21(ip + 27.93);
    //float rnd3 = hash21(ip + 57.75);
     
    // Random tile rotation.
    float iRnd = floor(rnd*4.);
    p = rot2(iRnd*3.14159/2.)*p;
    // Random tile flipping.
    //p.y *= (rnd>.5)? -1. : 1.;
    
    
    // Rendering the arcs onto the tile.
    //
    float d = 1e5, d1 = 1e5, d2 = 1e5, d3 = 1e5, l;
    
   
    // Three top left arcs.
    l = length(p - vec2(-.5, .5));
    d1 = abs(l - .25);
    d2 = abs(l - .5);
    d3 = abs(l - .75);
    if(rnd2>.33) d3 = abs(length(p - vec2(.125, .5)) - .125);
    
    d = min(min(d1, d2), d3);
    
    // Two small arcs on the bottom right.
    d1 = 1e5;//abs(length(p - vec2(.5, .5)) - .25);
    //if(rnd3>.35) d1 = 1e5;//
    d2 = abs(length(p - vec2(.5, .125)) - .125);
    d3 = abs(length(p - vec2(.5, -.5)) - .25);
    d = min(d, min(d1, min(d2, d3))); 
    
    
    // Three bottom left arcs.
    l = length(p + .5);
    d = max(d, -(l - .75)); // Outer mask.
    
    // Equivalent to the block below:
    //
    //d1 = abs(l - .75);
    //d2 = abs(l - .5);
    //d3 = abs(l - .25);
    //d = min(d, min(min(d1, d2), d3));
	//
    d1 = abs(l - .5);
    d1 = min(d1, abs(d1 - .25));
    d = min(d, d1);
    
    
    // Arc width. 
    d -= .0625;
    
 
    // Return the distance field value for the grid tile.
    return d; 
    
}


// Smooth fract function.
float sFract(float x, float sf){
    
    x = fract(x);
    return min(x, (1. - x)*x*sf);
    
}


// The grungey texture -- Kind of modelled off of the metallic Shadertoy texture,
// but not really. Most of it was made up on the spot, so probably isn't worth 
// commenting. However, for the most part, is just a mixture of colors using 
// noise variables.
vec3 GrungeTex(vec2 p){
    
 	// Some fBm noise.
    //float c = n2D(p*4.)*.66 + n2D(p*8.)*.34;
    float c = n2D(p*3.)*.57 + n2D(p*7.)*.28 + n2D(p*15.)*.15;
   
    // Noisey bluish red color mix.
    vec3 col = mix(vec3(.25, .1, .02), vec3(.35, .5, .65), c);
    // Running slightly stretched fine noise over the top.
    col *= n2D(p*vec2(150., 350.))*.5 + .5; 
    
    // Using a smooth fract formula to provide some splotchiness... Is that a word? :)
    col = mix(col, col*vec3(.75, .95, 1.2), sFract(c*4., 12.));
    col = mix(col, col*vec3(1.2, 1, .8)*.8, sFract(c*5. + .35, 12.)*.5);
    
    // More noise and fract tweaking.
    c = n2D(p*8. + .5)*.7 + n2D(p*18. + .5)*.3;
    c = c*.7 + sFract(c*5., 16.)*.3;
    col = mix(col*.6, col*1.4, c);
    
    // Clamping to a zero to one range.
    return clamp(col, 0., 1.);
    
}


void main(){
    
    
    vec2 fragCoord = gl_FragCoord.xy;

    // Aspect correct screen coordinates. Setting a minumum resolution on the
    // fullscreen setting in an attempt to keep things relatively crisp.
    float res = min(iResolution.y, 750.);
	vec2 uv = (fragCoord - iResolution.xy*.5)/res;
    
    // Scaling and translation.
    vec2 p = uv*4. + vec2(1, 0)*iTime;
    // Optional rotation, if you'd prefer.
    //vec2 p = rot2(3.14159/6.)*uv*4. + vec2(1, 0)*iTime;
    // Flockaroo's rotozoom suggestion, if that's more your speed. :)
    //vec2 p = rot2(sin(iTime/4.)*3.14159)*uv*(4.5 + 1.5*sin(iTime/4.)) + vec2(0, 1)*iTime;
    
    
    // Taking a few distance field readings.    
    vec2 eps = vec2(4, 6)/iResolution.y;
    float d = TilePattern(p); // Initial field value.
    float d2 = TilePattern(p + eps); // Slight sample distance, for highlighting,.
    float dS = TilePattern(p + eps*3.); // Larger distance, for shadows.
    
    // Calculating the sample difference.    
    float b = smoothstep(0., 15./450., d - .015);
    float b2 = smoothstep(0., 15./450., d2 - .015);
    
    // Bump value for the warm highlight (above), and the cool one (below).
    float bump = max(b2 - b, 0.)/length(eps);
    float bump2 = max(b - b2, 0.)/length(eps);
    
 
    
    // Smoothing factor, based on resolution.
    float sf = 5./iResolution.y;
     
    // The grungey texture.
    vec3 tx = GrungeTex(p/4. + .5);
    tx = smoothstep(0., .5, tx);
    
     
    // Background texture.
    vec3 bg = tx*vec3(.85, .68, .51);
   
    // Initiate the image color to the background.
    vec3 col = bg;
    
    

    // Displaying the grid, in order to see the individual grid tiles.
    #ifdef SHOW_GRID
    vec2 q = abs(fract(p) - .5);
	float gw = .0275;
    float grid = (max(q.x, q.y) - .5 + gw);
    col = mix(col, vec3(0), (smoothstep(0., sf*4., grid - gw + gw*2.))*.75);
    col = mix(col, bg*2., (smoothstep(0., sf, grid - gw + gw/2.)));
    #endif
    
     
    // Sometimes, more detail can help, but in this case, it's a bit much, I think. :)
    //float dP = TilePattern(p*5.);
    //col = mix(col, min(bg*2.5, 1.), sstep(sf*15., dP + .01)); // Pattern.
    //col = mix(col, bg/4., sstep(sf*5., dP + .03)); // Pattern.
     
    
    // TILE RENDERING.
    
    // Drop shadow -- blurred and slighly faded onto the background.
    col = mix(col, vec3(0), sstep(sf*4., dS - .02)*.75); // Shadow.
    
    // Blurred line -- subtle, and not entirely necessary, but it's there.
    col = mix(col, vec3(0), sstep(sf*8., d)*.35);
    
    // Dark edge line -- stroke.
    col = mix(col, vec3(0), sstep(sf, d));
     
    
    // Pattern color -- just a brightly colored version of the background.   
    vec3 pCol = vec3(2.5, .75, .25)*tx;
    // Uncomment this, if blue's more your thing.
    //pCol = pCol.zyx*1.2;
    
  
    // Apply the pattern color. Decrease the pattern width by the edge line width.
    col = mix(col, pCol, sstep(sf, d + .025));
     
    
    // Use some noise to mix the colors from orange to pink. Uncomment to see what it does.
    col = mix(col, col.xzy, smoothstep(.3, 1., fbm(p*.85))*.7);
    
    // Applying the warm sunlight bump value to the image, on the opposite side to the shadow.
    col = col + (vec3(1, .2, .1)*(bump*.01 + bump*bump*.003));
    // Applying the cool bump value to the image, on the shadow side.
    col = col + col*(vec3(1, .2, .1).zyx*(bump2*.01 + bump2*bump2*.003));   
 
    
    // Uncomment this to see the grungey texture on its own. Yeah, it's pretty basic,
    // so it won't be winning any awards, but it's suitable enough for this example. :)
    //col = tx;

    
    // Rough gamma correction.
    fragColor = vec4(sqrt(max(col, 0.)), 1);

}

