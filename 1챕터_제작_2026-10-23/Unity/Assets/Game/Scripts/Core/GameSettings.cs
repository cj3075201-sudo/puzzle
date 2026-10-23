using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OUAT.Core
{
    /// <summary>
    /// 플레이어 설정(PlayerPrefs에 저장, 게임을 켜면 바로 적용).
    /// 화면: 해상도·화면 모드·수직 동기화·최대 프레임·그래픽 품질·렌더 배율·밝기 / 소리: 전체·음악·효과음·환경음 /
    /// 게임: 화면 흔들림·글자 크기·커서 크기·말풍선 표시 시간.
    /// 다른 코드는 속성을 읽기만 하고, 바뀌면 Changed가 울린다.
    /// </summary>
    public static class GameSettings
    {
        // ── 소리 ──
        public static float MasterVolume = 1f, MusicVolume = 0.8f, SfxVolume = 1f, AmbientVolume = 0.8f;
        // ── 화면 ──
        public static int ResolutionWidth, ResolutionHeight;
        public static FullScreenMode ScreenMode = FullScreenMode.FullScreenWindow;
        public static bool VSync = true;
        /// <summary>최대 프레임(0 = 무제한). 수직 동기화가 켜져 있으면 쓰지 않음.</summary>
        public static int FrameLimit = 60;
        /// <summary>그래픽 품질 0 낮음 · 1 보통 · 2 높음.</summary>
        public static int Quality = 2;
        /// <summary>렌더 배율 0.5~1.0(URP renderScale).</summary>
        public static float RenderScale = 1f;
        /// <summary>밝기 -0.3(어둡게) ~ +0.3(밝게). UIRoot가 세계 위에 얇은 막으로 적용.</summary>
        public static float Brightness = 0f;
        // ── 게임 ──
        public static bool ScreenShake = true;
        /// <summary>세계 위 글자(말풍선·생각·표시·알림) 크기 배율 0.9~1.3.</summary>
        public static float UiScale = 1f;
        public static bool CursorLarge = false;
        /// <summary>말풍선 표시 시간 배율(짧게 0.7 · 보통 1 · 길게 1.5).</summary>
        public static float BalloonTime = 1f;

        public static readonly int[] FrameLimits = { 30, 60, 120, 144, 0 };
        public static readonly float[] BalloonTimes = { 0.7f, 1f, 1.5f };

        public static event Action Changed;
        static bool loaded;

        const string P = "ouat_set_";

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            Load();
            ApplyAll();
        }

        public static void Load()
        {
            loaded = true;
            MasterVolume = PlayerPrefs.GetFloat(P + "master", 1f);
            MusicVolume = PlayerPrefs.GetFloat(P + "music", 0.8f);
            SfxVolume = PlayerPrefs.GetFloat(P + "sfx", 1f);
            AmbientVolume = PlayerPrefs.GetFloat(P + "ambient", 0.8f);
            var cur = Screen.currentResolution;
            ResolutionWidth = PlayerPrefs.GetInt(P + "resw", Screen.fullScreenMode == FullScreenMode.Windowed ? Screen.width : cur.width);
            ResolutionHeight = PlayerPrefs.GetInt(P + "resh", Screen.fullScreenMode == FullScreenMode.Windowed ? Screen.height : cur.height);
            ScreenMode = (FullScreenMode)PlayerPrefs.GetInt(P + "mode", (int)Screen.fullScreenMode);
            VSync = PlayerPrefs.GetInt(P + "vsync", 1) == 1;
            FrameLimit = PlayerPrefs.GetInt(P + "fps", 60);
            Quality = Mathf.Clamp(PlayerPrefs.GetInt(P + "quality", 2), 0, 2);
            RenderScale = Mathf.Clamp(PlayerPrefs.GetFloat(P + "rscale", 1f), 0.5f, 1f);
            Brightness = Mathf.Clamp(PlayerPrefs.GetFloat(P + "bright", 0f), -0.3f, 0.3f);
            ScreenShake = PlayerPrefs.GetInt(P + "shake", 1) == 1;
            UiScale = Mathf.Clamp(PlayerPrefs.GetFloat(P + "uiscale", 1f), 0.9f, 1.3f);
            CursorLarge = PlayerPrefs.GetInt(P + "cursorL", 0) == 1;
            BalloonTime = Mathf.Clamp(PlayerPrefs.GetFloat(P + "balloon", 1f), 0.5f, 2f);
        }

        public static void Save()
        {
            PlayerPrefs.SetFloat(P + "master", MasterVolume);
            PlayerPrefs.SetFloat(P + "music", MusicVolume);
            PlayerPrefs.SetFloat(P + "sfx", SfxVolume);
            PlayerPrefs.SetFloat(P + "ambient", AmbientVolume);
            PlayerPrefs.SetInt(P + "resw", ResolutionWidth);
            PlayerPrefs.SetInt(P + "resh", ResolutionHeight);
            PlayerPrefs.SetInt(P + "mode", (int)ScreenMode);
            PlayerPrefs.SetInt(P + "vsync", VSync ? 1 : 0);
            PlayerPrefs.SetInt(P + "fps", FrameLimit);
            PlayerPrefs.SetInt(P + "quality", Quality);
            PlayerPrefs.SetFloat(P + "rscale", RenderScale);
            PlayerPrefs.SetFloat(P + "bright", Brightness);
            PlayerPrefs.SetInt(P + "shake", ScreenShake ? 1 : 0);
            PlayerPrefs.SetFloat(P + "uiscale", UiScale);
            PlayerPrefs.SetInt(P + "cursorL", CursorLarge ? 1 : 0);
            PlayerPrefs.SetFloat(P + "balloon", BalloonTime);
            PlayerPrefs.Save();
        }

        public static void EnsureLoaded() { if (!loaded) Load(); }

        /// <summary>모든 설정 적용(화면 해상도 포함).</summary>
        public static void ApplyAll()
        {
            ApplyResolution();
            ApplyGraphics();
            ApplyAudio();
            NotifyChanged();
        }

        /// <summary>소리·게임 설정이 바뀌었을 때(가벼운 것). 듣는 쪽(AudioHub·UIRoot)에 알린다.</summary>
        public static void NotifyChanged() { try { Changed?.Invoke(); } catch (Exception e) { Debug.LogException(e); } }

        public static void ApplyAudio() { AudioListener.volume = Mathf.Clamp01(MasterVolume); }

        public static void ApplyResolution()
        {
            if (ResolutionWidth <= 0 || ResolutionHeight <= 0) return;
            if (Application.isEditor) return;   // 에디터 게임 창 크기는 건드리지 않음
            Screen.SetResolution(ResolutionWidth, ResolutionHeight, ScreenMode);
        }

        static readonly string[][] QualityNames = { new[] { "Low", "Very Low" }, new[] { "Medium" }, new[] { "High", "Very High", "Ultra" } };

        /// <summary>품질 단계 → 수직 동기화 → 프레임 → URP(렌더 배율·그림자·MSAA) 순서로 적용(품질을 바꾸면 vSync가 단계 값으로 돌아가므로).</summary>
        public static void ApplyGraphics()
        {
            int level = FindQualityLevel(Quality);
            if (level >= 0 && level != QualitySettings.GetQualityLevel()) QualitySettings.SetQualityLevel(level, true);
            QualitySettings.vSyncCount = VSync ? 1 : 0;
            Application.targetFrameRate = VSync ? -1 : (FrameLimit <= 0 ? -1 : FrameLimit);
            ApplyUrp();
        }

        static int FindQualityLevel(int q)
        {
            var names = QualitySettings.names;
            foreach (var want in QualityNames[Mathf.Clamp(q, 0, 2)])
                for (int i = 0; i < names.Length; i++) if (names[i] == want) return i;
            if (names.Length == 0) return -1;
            return Mathf.Clamp(Mathf.RoundToInt(q / 2f * (names.Length - 1)), 0, names.Length - 1);
        }

        static bool origSaved;
        static float origScale, origShadow; static int origMsaa;

        static void ApplyUrp()
        {
            var urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (urp == null) return;
            if (!origSaved)
            {
                origSaved = true; origScale = urp.renderScale; origShadow = urp.shadowDistance; origMsaa = urp.msaaSampleCount;
                if (Application.isEditor) Application.quitting += RestoreUrp;   // 에디터에서는 에셋이 바뀐 채로 남지 않게
            }
            urp.renderScale = Mathf.Clamp(RenderScale, 0.5f, 1f);
            urp.shadowDistance = Quality == 0 ? 0f : Quality == 1 ? Mathf.Min(origShadow, 50f) : origShadow;
            urp.msaaSampleCount = Quality == 0 ? 1 : Quality == 1 ? 2 : Mathf.Max(1, origMsaa);
        }

        static void RestoreUrp()
        {
            var urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (urp == null || !origSaved) return;
            urp.renderScale = origScale; urp.shadowDistance = origShadow; urp.msaaSampleCount = origMsaa;
        }

        /// <summary>이 모니터가 지원하는 해상도(가로·세로 중복 제거, 작은 것부터).</summary>
        public static List<Vector2Int> Resolutions()
        {
            var list = Screen.resolutions.Select(r => new Vector2Int(r.width, r.height)).Where(v => v.x >= 800 && v.y >= 600).Distinct().OrderBy(v => v.x).ThenBy(v => v.y).ToList();
            var cur = new Vector2Int(ResolutionWidth > 0 ? ResolutionWidth : Screen.width, ResolutionHeight > 0 ? ResolutionHeight : Screen.height);
            if (!list.Contains(cur)) { list.Add(cur); list = list.OrderBy(v => v.x).ThenBy(v => v.y).ToList(); }
            return list;
        }

        public enum Section { Display, Sound, Game }

        public static void ResetDefaults(Section s)
        {
            switch (s)
            {
                case Section.Sound: MasterVolume = 1f; MusicVolume = 0.8f; SfxVolume = 1f; AmbientVolume = 0.8f; ApplyAudio(); break;
                case Section.Game: ScreenShake = true; UiScale = 1f; CursorLarge = false; BalloonTime = 1f; break;
                case Section.Display:
                    var cur = Screen.currentResolution;
                    ResolutionWidth = cur.width; ResolutionHeight = cur.height; ScreenMode = FullScreenMode.FullScreenWindow;
                    VSync = true; FrameLimit = 60; Quality = 2; RenderScale = 1f; Brightness = 0f;
                    ApplyResolution(); ApplyGraphics();
                    break;
            }
            Save();
            NotifyChanged();
        }
    }
}
