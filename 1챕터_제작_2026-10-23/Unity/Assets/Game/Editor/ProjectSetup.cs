// 프로젝트 설정을 코드로 맞춘다: URP 파이프라인 자산, 선형 색 공간, 제품 이름, UI Toolkit 패널 설정.
// 배치 실행: tools/unity.ps1 -Method OUAT.EditorTools.ProjectSetup.Run
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.UIElements;

namespace OUAT.EditorTools
{
    public static class ProjectSetup
    {
        const string SettingsDir = "Assets/Game/Settings";
        public const string UrpAssetPath = SettingsDir + "/OUAT_URP.asset";
        public const string RendererPath = SettingsDir + "/OUAT_Renderer.asset";
        public const string PanelSettingsPath = "Assets/Game/Resources/UI/OUAT_PanelSettings.asset";

        [MenuItem("OUAT/Setup Project")]
        public static void Run()
        {
            EnsureFolder(SettingsDir);
            EnsureFolder("Assets/Game/Resources/UI");

            PlayerSettings.companyName = "Serate";
            PlayerSettings.productName = "Once Under a Time";
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.defaultScreenWidth = 1920;
            PlayerSettings.defaultScreenHeight = 1080;
            PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
            PlayerSettings.resizableWindow = true;
            PlayerSettings.runInBackground = true;

            var urp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(UrpAssetPath);
            if (urp == null)
            {
                var rendererData = ScriptableObject.CreateInstance<UniversalRendererData>();
                AssetDatabase.CreateAsset(rendererData, RendererPath);
                urp = UniversalRenderPipelineAsset.Create(rendererData);
                AssetDatabase.CreateAsset(urp, UrpAssetPath);
            }
            urp.msaaSampleCount = 4;
            urp.renderScale = 1f;
            urp.supportsHDR = true;
            urp.shadowDistance = 90f;
            urp.shadowCascadeCount = 2;
            EditorUtility.SetDirty(urp);

            EnsureInkFeature();
            GraphicsSettings.defaultRenderPipeline = urp;
            for (int i = 0; i < QualitySettings.names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                QualitySettings.renderPipeline = urp;
            }
            QualitySettings.SetQualityLevel(QualitySettings.names.Length - 1, false);

            var panel = AssetDatabase.LoadAssetAtPath<PanelSettings>(PanelSettingsPath);
            if (panel == null)
            {
                panel = ScriptableObject.CreateInstance<PanelSettings>();
                AssetDatabase.CreateAsset(panel, PanelSettingsPath);
            }
            panel.scaleMode = PanelScaleMode.ScaleWithScreenSize;
            panel.referenceResolution = new Vector2Int(1920, 1080);
            panel.screenMatchMode = PanelScreenMatchMode.MatchWidthOrHeight;
            panel.match = 0.5f;
            panel.themeStyleSheet = AssetDatabase.LoadAssetAtPath<ThemeStyleSheet>("Assets/Game/Resources/UI/OUATTheme.tss");
            panel.clearColor = false;
            EditorUtility.SetDirty(panel);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[OUAT] ProjectSetup done");
        }

        /// <summary>화면 전체 잉크 선·종이 결 후처리(FullScreenPassRendererFeature)를 렌더러에 한 번만 단다.</summary>
        static void EnsureInkFeature()
        {
            var data = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererPath);
            if (data == null) return;
            var shader = Shader.Find("OUAT/InkPaper");
            if (shader == null) { Debug.LogWarning("[OUAT] InkPaper 셰이더 없음"); return; }
            var matPath = "Assets/Game/Settings/OUAT_InkPaper.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (mat == null) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, matPath); }
            mat.shader = shader;
            FullScreenPassRendererFeature feature = null;
            foreach (var f in data.rendererFeatures) if (f is FullScreenPassRendererFeature fs && f.name == "InkPaper") feature = fs;
            if (feature == null)
            {
                feature = ScriptableObject.CreateInstance<FullScreenPassRendererFeature>();
                feature.name = "InkPaper";
                AssetDatabase.AddObjectToAsset(feature, data);
                data.rendererFeatures.Add(feature);
                var so = new SerializedObject(data);
                var map = so.FindProperty("m_RendererFeatureMap");
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(feature, out string _, out long localId);
                map.arraySize++;
                map.GetArrayElementAtIndex(map.arraySize - 1).longValue = localId;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            feature.passMaterial = mat;
            feature.injectionPoint = FullScreenPassRendererFeature.InjectionPoint.BeforeRenderingPostProcessing;
            feature.requirements = ScriptableRenderPassInput.Depth | ScriptableRenderPassInput.Normal | ScriptableRenderPassInput.Color;
            feature.fetchColorBuffer = true;
            feature.SetActive(true);
            EditorUtility.SetDirty(feature);
            EditorUtility.SetDirty(data);
        }

        public static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            var parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }
    }
}
