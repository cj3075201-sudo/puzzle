// 그리다 만 그림책 툰 셰이더: 2단 음영 + 그늘 면 손그림 빗금 + 잉크 외곽선(뒤집은 껍데기).
// _Paint = 0이면 종이처럼 칠이 빠진 상태(그리다 만), 1이면 다 칠해진 상태.
Shader "OUAT/Toon"
{
    Properties
    {
        _BaseColor ("Base Color", Color) = (0.945, 0.933, 0.902, 1)
        _ShadeColor ("Shade Color", Color) = (0.79, 0.80, 0.81, 1)
        _BaseMap ("Base Map", 2D) = "white" {}
        _Paint ("Paint Amount", Range(0,1)) = 1
        _PaperColor ("Paper Color", Color) = (0.945, 0.933, 0.902, 1)
        _ShadeThreshold ("Shade Threshold", Range(-1,1)) = 0.15
        _ShadeSoftness ("Shade Softness", Range(0.001,0.5)) = 0.05
        _HatchColor ("Hatch Color", Color) = (0.36, 0.38, 0.42, 1)
        _HatchStrength ("Hatch Strength", Range(0,1)) = 0.55
        _HatchScale ("Hatch Lines Per Meter", Float) = 9
        _OutlineColor ("Outline Color", Color) = (0.169, 0.149, 0.133, 1)
        _OutlineWidth ("Outline Width", Range(0,0.08)) = 0.022
        _Emission ("Emission", Color) = (0,0,0,0)
        _Highlight ("Highlight", Range(0,1)) = 0
        _HighlightColor ("Highlight Color", Color) = (1, 0.82, 0.45, 1)
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
        _KeepColor ("Keep Color (human things, hero)", Range(0,1)) = 0
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            float4 _BaseColor;
            float4 _ShadeColor;
            float4 _BaseMap_ST;
            float _Paint;
            float4 _PaperColor;
            float _ShadeThreshold;
            float _ShadeSoftness;
            float4 _HatchColor;
            float _HatchStrength;
            float _HatchScale;
            float4 _OutlineColor;
            float _OutlineWidth;
            float4 _Emission;
            float _Highlight;
            float4 _HighlightColor;
            float _Cull;
            float _KeepColor;
        CBUFFER_END
        // 구역 분위기(AreaSystem이 Shader.SetGlobal…): 땅 밑 세계 — 빛구멍 아래만 밝고 나머지는 어둑하고 색이 빠짐
        float4 _OUAT_Ambient;    // a = 0이면 쓰지 않음(편집기)
        float _OUAT_Drain;
        float4 _OUAT_DrainTint;
        float3 OuatMood(float3 col, float3 lightLevel, float keep)
        {
            if (_OUAT_Ambient.a > 0) col *= lightLevel;
            float lum = dot(col, float3(0.3, 0.59, 0.11));
            float3 tint = _OUAT_DrainTint.a > 0 ? _OUAT_DrainTint.rgb : float3(1, 1, 1);
            return lerp(col, lum * tint, saturate(_OUAT_Drain) * (1 - keep));
        }
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);

        float Hash21(float2 p)
        {
            p = frac(p * float2(123.34, 456.21));
            p += dot(p, p + 45.32);
            return frac(p.x * p.y);
        }
        ENDHLSL

        Pass
        {
            Name "ToonForward"
            Tags { "LightMode"="UniversalForward" }
            Cull [_Cull]
            ZWrite On

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile _ _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; float4 color : COLOR; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float2 uv : TEXCOORD2;
                float4 color : COLOR;
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                VertexPositionInputs p = GetVertexPositionInputs(v.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.positionWS = p.positionWS;
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
                o.color = v.color;
                return o;
            }

            // 세 축 손그림 빗금: 면 방향에 따라 사선 줄을 섞고 선 굵기를 조금씩 흔든다.
            float Hatch(float3 pos, float3 n)
            {
                float3 w = abs(n); w = w / (w.x + w.y + w.z + 1e-4);
                float s = _HatchScale;
                float a = frac((pos.y + pos.z * 0.6) * s);
                float b = frac((pos.x + pos.y * 0.6) * s);
                float c = frac((pos.x + pos.z * 0.75) * s);
                float jitterA = Hash21(floor(float2(pos.y, pos.z) * s)) * 0.25;
                float jitterB = Hash21(floor(float2(pos.x, pos.y) * s)) * 0.25;
                float jitterC = Hash21(floor(float2(pos.x, pos.z) * s)) * 0.25;
                float la = smoothstep(0.18 + jitterA, 0.0, abs(a - 0.5) - 0.32);
                float lb = smoothstep(0.18 + jitterB, 0.0, abs(b - 0.5) - 0.32);
                float lc = smoothstep(0.18 + jitterC, 0.0, abs(c - 0.5) - 0.32);
                return saturate(la * w.x + lb * w.z + lc * w.y);
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 n = normalize(i.normalWS);
                if (dot(n, GetWorldSpaceViewDir(i.positionWS)) < 0) n = -n;   // 양면일 때 뒤집힌 면도 바르게 비춤
                float4 shadowCoord = TransformWorldToShadowCoord(i.positionWS);
                Light mainLight = GetMainLight(shadowCoord);
                float ndl = dot(n, mainLight.direction);
                float lit = smoothstep(_ShadeThreshold - _ShadeSoftness, _ShadeThreshold + _ShadeSoftness, ndl);
                lit *= lerp(0.0, 1.0, mainLight.shadowAttenuation);

                float3 tex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).rgb;
                float3 painted = _BaseColor.rgb * tex * i.color.rgb;
                float3 base = lerp(_PaperColor.rgb, painted, _Paint);
                float3 shade = lerp(_PaperColor.rgb * _ShadeColor.rgb, _ShadeColor.rgb * painted, _Paint);
                float3 col = lerp(shade, base, lit);

                float h = Hatch(i.positionWS, n) * (1.0 - lit) * _HatchStrength;
                col = lerp(col, _HatchColor.rgb, h);

                // 빛의 양: 둘레빛 + 주광 + 보조 광원(빛줄기·등불, 2단으로 끊어서)
                float3 level = _OUAT_Ambient.rgb + mainLight.color * lit;
                #if defined(_ADDITIONAL_LIGHTS)
                uint count = GetAdditionalLightsCount();
                for (uint li = 0u; li < count; li++)
                {
                    Light l = GetAdditionalLight(li, i.positionWS, 1);
                    float a = l.distanceAttenuation * l.shadowAttenuation * saturate(dot(n, l.direction) * 0.6 + 0.4);
                    float k = smoothstep(0.02, 0.06, a) * 0.55 + smoothstep(0.12, 0.2, a) * 0.45;
                    level += l.color * k * min(a * 4, 1.0);
                }
                #endif
                col = OuatMood(col, level, _KeepColor);
                col += _Emission.rgb;
                col = lerp(col, _HighlightColor.rgb, _Highlight * 0.35);
                return half4(col, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "InkOutline"
            Tags { "LightMode"="SRPDefaultUnlit" }
            Cull Front
            ZWrite On

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; float wob : TEXCOORD0; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                float3 posWS = TransformObjectToWorld(v.positionOS.xyz);
                float3 nWS = normalize(TransformObjectToWorldNormal(v.normalOS));
                float dist = distance(_WorldSpaceCameraPos.xyz, posWS);
                // 손으로 그은 선처럼 굵기를 조금 흔든다
                float wob = 0.75 + 0.5 * Hash21(floor(posWS.xz * 3.0) + floor(posWS.y * 3.0));
                float w = _OutlineWidth * wob * clamp(dist * 0.06, 0.6, 2.2);
                posWS += nWS * w;
                o.positionCS = TransformWorldToHClip(posWS);
                o.wob = wob;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 c = lerp(_OutlineColor.rgb, _HighlightColor.rgb, _Highlight);
                if (_OUAT_Ambient.a > 0) c *= lerp(1, 0.75, saturate(_OUAT_Drain));
                return half4(c, 1);
            }
            ENDHLSL
        }

        UsePass "Universal Render Pipeline/Lit/ShadowCaster"
        UsePass "Universal Render Pipeline/Lit/DepthOnly"
        UsePass "Universal Render Pipeline/Lit/DepthNormals"
    }
}
