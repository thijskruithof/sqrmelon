float fTestModel(vec3 p)
{
	vec4 p4 = vec4(p, 1.0);

	float d = 99999.0;
	d = min(d, fBox((p4*mat4(0.895620,-0.414347,-0.161805,0.607261,0.199510,0.049072,0.978666,0.010925,-0.397568,-0.908795,0.126616,0.380592,0.000000,0.000000,-0.000000,1.000000)).xyz, vec3(0.306958,0.333201,0.057406)));
	d = min(d, fBox((p4*mat4(-0.187845,-0.034162,-0.981604,-0.105587,-0.904165,0.396399,0.159231,-0.876332,0.383667,0.917443,-0.105349,-0.340717,0.000000,0.000000,0.000000,1.000000)).xyz, vec3(1.000000,1.000000,0.050000)));
	d = min(d, fBox((p4*mat4(1.000000,0.000000,0.000000,0.755754,0.000000,1.000000,0.000000,0.547557,0.000000,0.000000,1.000000,0.027177,0.000000,0.000000,0.000000,1.000000)).xyz, vec3(0.751873,0.125000,0.156539)));
	d = min(d, fBox((p4*mat4(0.864789,-0.481802,-0.141445,0.592441,-0.173735,-0.022806,-0.984529,-0.001759,0.471122,0.875984,-0.103428,-0.793454,0.000000,0.000000,0.000000,1.000000)).xyz, vec3(0.125000,0.125000,0.593051)));
	d = min(d, fBox((p4*mat4(1.000000,0.000000,0.000000,0.871564,0.000000,1.000000,0.000000,0.037929,0.000000,0.000000,1.000000,0.027177,0.000000,0.000000,0.000000,1.000000)).xyz, vec3(0.751873,0.125000,0.156539)));
	return d;
}