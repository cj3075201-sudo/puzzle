// 화면 전체 후처리: 깊이·법선 경계에 손으로 그은 듯한 잉크 선 + 종이 결 + 가장자리 바램.
// 모든 물체가 같은 선 언어로 그려져 “그리다 만 그림책”이 한 장의 그림처럼 묶이게 한다.
Shader "OUAT/InkPaper"
{
    Properties
    {
        _InkColor ("Ink", Color) = (0.169, 0.149, 0.133, 1)
        _LineWidth ("Line Width (px)", Range(0.5, 3)) = 1.3
        _DepthSens ("Depth Sensitivity", Range(0, 50)) = 18
        _NormalSens ("Normal Sensitivity", Range(0, 4)) = 1.1
        _LineStrength ("Line Strength", Range(0, 1)) = 0.9
        _FarFade ("Far Fade (m)", Float) = 140
        _Grain ("Paper Grain", Range(0, 0.2)) = 0.045
        _Edge ("Page Edge Fade", Range(0, 1)) = 0.35
        _PaperColor ("Paper", Color) = (0.945, 0.933, 0.902, 1)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        ZWrite Off Cull Off ZTest Always
        Pass
        {
            Name "InkPaper"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.core/Runtime/Utilities/Blit.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareNormalsTexture.hlsl"

            float4 _InkColor; float _LineWidth; float _DepthSens; float _NormalSens; float _LineStrength; float _FarFade; float _Grain; float _Edge; float4 _PaperColor;
            float4 _OUAT_EdgeColor;   // 구역 분위기: 화면 가장자리가 바래 가는 색(어둑한 종이)

            float Hash(float2 p) { p = frac(p * float2(443.897, 441.423)); p += dot(p, p.yx + 19.19); return frac((p.x + p.y) * p.x); }
            float Noise(float2 p)
            {
                float2 i = floor(p), f = frac(p); f = f * f * (3 - 2 * f);
                return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), f.x), lerp(Hash(i + float2(0, 1)), Hash(i + 1), f.x), f.y);
            }

            float Edge(float2 uv, float2 texel)
            {
                float d0 = LinearEyeDepth(SampleSceneDepth(uv), _ZBufferParams);
                float3 n0 = SampleSceneNormals(uv);
                float e = 0;
                const float2 offs[4] = { float2(1, 0), float2(-1, 0), float2(0, 1), float2(0, -1) };
                [unroll] for (int k = 0; k < 4; k++)
                {
                    float2 o = uv + offs[k] * texel;
                    float d = LinearEyeDepth(SampleSceneDepth(o), _ZBufferParams);
                    float3 n = SampleSceneNormals(o);
                    e = max(e, saturate(abs(d - d0) / max(d0, 0.5) * _DepthSens - 0.25));
                    e = max(e, saturate((1 - dot(n, n0)) * _NormalSens * 3 - 0.35));
                }
                return e * saturate(1 - d0 / _FarFade);
            }

            half4 Frag(Varyings i) : SV_Target
            {
                float2 uv = i.texcoord;
                half4 col = SAMPLE_TEXTURE2D_X(_BlitTexture, sampler_LinearClamp, uv);
                float2 px = uv * _ScreenParams.xy;
                // 손떨림: 선 표본 위치를 조금 흔든다
                float2 wob = (float2(Noise(px * 0.035), Noise(px * 0.035 + 17.3)) - 0.5) * 1.6;
                float2 texel = _LineWidth / _ScreenParams.xy;
                float e = Edge(uv + wob / _ScreenParams.xy, texel);
                // 선이 군데군데 끊기고 농담이 달라지게
                float breakup = smoothstep(0.15, 0.55, Noise(px * 0.02 + 3.1));
                float ink = saturate(e * _LineStrength * (0.55 + 0.45 * breakup));
                col.rgb = lerp(col.rgb, _InkColor.rgb, ink);
                // 종이 결
                float g = (Noise(px * 0.9) - 0.5) * 0.6 + (Noise(px * 0.12) - 0.5) * 0.4;
                col.rgb *= 1 + g * _Grain;
                // 가장자리: 종이 쪽으로 바래게(그림책 한 쪽처럼)
                float2 c = uv - 0.5; c.x *= _ScreenParams.x / _ScreenParams.y;
                float r = length(c * float2(0.85, 1.05));
                float fade = smoothstep(0.62, 1.05, r + (Noise(px * 0.01) - 0.5) * 0.12) * _Edge;
                col.rgb = lerp(col.rgb, _OUAT_EdgeColor.a > 0 ? _OUAT_EdgeColor.rgb : _PaperColor.rgb, fade);
                return col;
            }
            ENDHLSL
        }
    }
}
