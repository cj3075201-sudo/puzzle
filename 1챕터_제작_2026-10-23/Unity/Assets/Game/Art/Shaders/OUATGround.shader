// 그리다 만 바닥: 흰 종이 + 선으로만 그린 육각 돌길 + 그늘의 빗금. _HexAmount로 돌길 선을 켜고 끈다.
Shader "OUAT/Ground"
{
    Properties
    {
        _PaperColor ("Paper Color", Color) = (0.945, 0.933, 0.902, 1)
        _ShadeColor ("Shade Color", Color) = (0.80, 0.81, 0.83, 1)
        _LineColor ("Line Color", Color) = (0.169, 0.149, 0.133, 1)
        _HexSize ("Hex Size (m)", Float) = 1.6
        _HexAmount ("Hex Lines", Range(0,1)) = 1
        _LineWidth ("Line Width", Range(0.005,0.12)) = 0.018
        _HatchStrength ("Hatch Strength", Range(0,1)) = 0.5
        _HatchScale ("Hatch Lines Per Meter", Float) = 8
        _Tint ("Painted Tint", Color) = (1,1,1,0)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Pass
        {
            Name "GroundForward"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile _ _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            CBUFFER_START(UnityPerMaterial)
                float4 _PaperColor; float4 _ShadeColor; float4 _LineColor;
                float _HexSize; float _HexAmount; float _LineWidth; float _HatchStrength; float _HatchScale; float4 _Tint;
            CBUFFER_END
            float4 _OUAT_Ambient; float _OUAT_Drain; float4 _OUAT_DrainTint;

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; float3 normalWS : TEXCOORD1; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                VertexPositionInputs p = GetVertexPositionInputs(v.positionOS.xyz);
                o.positionCS = p.positionCS; o.positionWS = p.positionWS;
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                return o;
            }

            float Hash21(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }
            float Noise(float2 p)
            {
                float2 i = floor(p), f = frac(p); f = f * f * (3 - 2 * f);
                return lerp(lerp(Hash21(i), Hash21(i + float2(1,0)), f.x), lerp(Hash21(i + float2(0,1)), Hash21(i + 1), f.x), f.y);
            }
            // 육각 격자까지의 거리(가장자리 = 0)
            float HexEdge(float2 p)
            {
                const float2 s = float2(1, 1.7320508);
                float4 hc = floor(float4(p, p - float2(0.5, 1)) / s.xyxy) + 0.5;
                float4 h = float4(p - hc.xy * s, p - (hc.zw + 0.5) * s);
                float2 q = dot(h.xy, h.xy) < dot(h.zw, h.zw) ? h.xy : h.zw;
                q = abs(q);
                return 0.5 - max(dot(q, s * 0.5), q.x);
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 n = normalize(i.normalWS);
                Light l = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                float lit = smoothstep(0.05, 0.25, dot(n, l.direction)) * l.shadowAttenuation;
                float3 col = lerp(_PaperColor.rgb * _ShadeColor.rgb, _PaperColor.rgb, lit);
                col = lerp(col, col * _Tint.rgb, _Tint.a);

                float2 uv = i.positionWS.xz / _HexSize;
                uv += (float2(Noise(uv * 1.7), Noise(uv * 1.7 + 7.1)) - 0.5) * 0.18; // 손그림 흔들림
                float e = HexEdge(uv);
                float gap = Noise(uv * 3.1 + 2.0);                                    // 선이 군데군데 끊김(그리다 만)
                float w = _LineWidth * (0.7 + 0.6 * Noise(uv * 5.0));
                float hexLine = (1 - smoothstep(w, w + 0.02, e)) * step(0.28, gap) * _HexAmount;
                col = lerp(col, _LineColor.rgb, hexLine * 0.55);

                float hatch = frac((i.positionWS.x + i.positionWS.z * 0.6) * _HatchScale);
                float hl = smoothstep(0.16, 0.0, abs(hatch - 0.5) - 0.34) * (1 - lit) * _HatchStrength;
                col = lerp(col, _LineColor.rgb * 1.6, hl * 0.5);
                // 구역 분위기: 빛의 양(둘레빛 + 주광 + 빛줄기·등불) → 색 빠짐
                if (_OUAT_Ambient.a > 0)
                {
                    float3 level = _OUAT_Ambient.rgb + l.color * lit;
                    #if defined(_ADDITIONAL_LIGHTS)
                    uint cnt = GetAdditionalLightsCount();
                    for (uint li = 0u; li < cnt; li++)
                    {
                        Light al = GetAdditionalLight(li, i.positionWS, 1);
                        float a = al.distanceAttenuation * al.shadowAttenuation * saturate(dot(n, al.direction) * 0.6 + 0.4);
                        float k = smoothstep(0.02, 0.06, a) * 0.55 + smoothstep(0.12, 0.2, a) * 0.45;
                        level += al.color * k * min(a * 4, 1.0);
                    }
                    #endif
                    col *= level;
                    float lum = dot(col, float3(0.3, 0.59, 0.11));
                    col = lerp(col, lum * (_OUAT_DrainTint.a > 0 ? _OUAT_DrainTint.rgb : 1), saturate(_OUAT_Drain));
                }
                return half4(col, 1);
            }
            ENDHLSL
        }
        UsePass "Universal Render Pipeline/Lit/ShadowCaster"
        UsePass "Universal Render Pipeline/Lit/DepthOnly"
    }
}
