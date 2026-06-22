#version 300 es
precision highp float;

// Attributes provided by p5.js automatically
in vec3 aPosition;
in vec3 aNormal;
in vec2 aTexCoord;

// Matrices for coordinate transformation
uniform mat4 uModelViewMatrix;
uniform mat4 uProjectionMatrix;
uniform mat3 uNormalMatrix;   // Used to transform normals correctly

// Varying variables to pass data to the fragment shader
out vec2 vTexCoord;
out vec3 vNormal;

void main() {
  // Apply camera and object transforms to the position
  vec4 viewModelPosition = uModelViewMatrix * vec4(aPosition, 1.0);
  gl_Position = uProjectionMatrix * viewModelPosition;

  // Pass along texture coordinates
  vTexCoord = aTexCoord;

  // Transform the normal to world/view space and pass it along
  vNormal = uNormalMatrix * aNormal;
}

