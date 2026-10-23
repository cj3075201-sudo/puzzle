// 선·실루엣·스케치·빛 재질(art_materials.json의 line / silhouette / sketch / light 분류). 조명 없이 색 그대로.
Shader "OUAT/Unlit"
{
    Properties
    {
        _BaseColor ("Color", Color) = (0.169, 0.149, 0.133, 1)
        _BaseMap ("Texture", 2D) = "white" {}
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src Blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst Blend", Float) = 0
        [Enum(Off,0,On,1)] _ZWrite ("ZWrite", Float) = 1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 0
        _Wobble ("Sketch Wobble", Range(0,1)) = 0
        _Highlight ("Highlight", Range(0,1)) = 0
        _HighlightColor ("Highlight Color", Color) = (1, 0.82, 0.45, 1)
        _FadeUp ("Fade Toward Top", Range(0,1)) = 0
        _AmbientMul ("Dim With Area Light", Range(0,1)) = 0
        _KeepColor ("Keep Color", Range(0,1)) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Pass
        {
            Name "Unlit"
            Tags { "LightMode"="UniversalForward" }
            Blend [_SrcBlend] [_DstBlend]
            ZWrite [_ZWrite]
            Cull [_Cull]
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseColor; float4 _BaseMap_ST; float _Wobble; float _Highlight; float4 _HighlightColor; float _FadeUp;
                float _SrcBlend; float _DstBlend; float _ZWrite; float _Cull; float _AmbientMul; float _KeepColor;
            CBUFFER_END
            float4 _OUAT_Ambient; float _OUAT_Drain; float4 _OUAT_DrainTint;
            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            struct A { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct V { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 posWS : TEXCOORD1; };
            V vert(A i)
            {
                V o;
                float3 p = TransformObjectToWorld(i.positionOS.xyz);
                p += _Wobble * 0.02 * float3(sin(p.y * 17 + _Time.y * 2), 0, cos(p.y * 13 + _Time.y * 1.7));
                o.positionCS = TransformWorldToHClip(p);
                o.uv = TRANSFORM_TEX(i.uv, _BaseMap);
                o.posWS = p;
                return o;
            }
            half4 frag(V i) : SV_Target
            {
                half4 c = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv) * _BaseColor;
                c.rgb = lerp(c.rgb, _HighlightColor.rgb, _Highlight * 0.5);
                c.a *= lerp(1, saturate(1 - i.uv.y), _FadeUp);
                if (_OUAT_Ambient.a > 0)
                {
                    c.rgb *= lerp(float3(1, 1, 1), _OUAT_Ambient.rgb * 1.6, _AmbientMul);
                    float lum = dot(c.rgb, float3(0.3, 0.59, 0.11));
                    c.rgb = lerp(c.rgb, lum * (_OUAT_DrainTint.a > 0 ? _OUAT_DrainTint.rgb : 1), saturate(_OUAT_Drain) * (1 - _KeepColor));
                }
                return c;
            }
            ENDHLSL
        }
    }
}
