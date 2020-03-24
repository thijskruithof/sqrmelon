void main()
{
    vec3 p=(gl_FragCoord.xyz*2-uResolution.xxx)/uResolution.xxx;

    float k = length(p) - 1.0;

    outColor0=vec4(k,k,k,k);
}
