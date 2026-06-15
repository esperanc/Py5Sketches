#version 300 es
in vec3 aPosition;
in vec2 aTexCoord;

uniform mat4 uModelViewMatrix;
uniform mat4 uProjectionMatrix;

out vec2 v_texCoord;

void main() {
  // Pass the UV coordinates to the fragment shader
  v_texCoord = aTexCoord;
  
  // Calculate the standard screen position of the vertex
  gl_Position = uProjectionMatrix * uModelViewMatrix * vec4(aPosition, 1.0);
}