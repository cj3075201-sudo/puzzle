using System.Collections.Generic;
using UnityEngine;

namespace OUAT.Core
{
    /// <summary>
    /// 효과음과 바탕 소리. 녹음 소스가 없을 때도 게임처럼 들리도록 짧은 소리를 코드로 합성한다
    /// (종이 넘김, 나무 조각 딸깍, 쇠 걸쇠, 확정 종소리, 갸웃 낮은 소리, 동굴 바람). Resources/Audio/이름 이 있으면 그것을 우선.
    /// </summary>
    public class AudioHub : MonoBehaviour
    {
        static AudioHub inst;
        readonly Dictionary<string, AudioClip> clips = new Dictionary<string, AudioClip>();
        AudioSource sfx, amb, musicA, musicB;
        string currentMusic;
        const int Rate = 44100;
        // 소리 버스(설정 창): 전체 = AudioListener.volume, 음악·효과음·환경음은 각 소스에 곱함
        const float AmbBase = 0.22f;
        float musicBase = 0.38f;
        bool fading;
        Coroutine musicFade, ambFade;
        string currentAmb = "ambient";
        readonly Dictionary<string, AudioSource> loops = new Dictionary<string, AudioSource>();

        void Awake()
        {
            inst = this;
            sfx = gameObject.AddComponent<AudioSource>(); sfx.playOnAwake = false;
            amb = gameObject.AddComponent<AudioSource>(); amb.loop = true; amb.volume = 0.22f;
            amb.clip = Get("ambient"); amb.Play();
            musicA = gameObject.AddComponent<AudioSource>(); musicA.loop = true; musicA.volume = 0f;
            musicB = gameObject.AddComponent<AudioSource>(); musicB.loop = true; musicB.volume = 0f;
            GameSettings.EnsureLoaded();
            GameSettings.Changed += ApplyBuses;
            ApplyBuses();
        }

        void OnDestroy() { GameSettings.Changed -= ApplyBuses; }

        void ApplyBuses()
        {
            GameSettings.ApplyAudio();
            if (sfx) sfx.volume = Mathf.Clamp01(GameSettings.SfxVolume);
            if (amb) amb.volume = AmbBase * Mathf.Clamp01(GameSettings.AmbientVolume);
            if (!fading)
            {
                var on = musicA && musicA.isPlaying ? musicA : musicB && musicB.isPlaying ? musicB : null;
                if (on) on.volume = musicBase * Mathf.Clamp01(GameSettings.MusicVolume);
            }
        }

        /// <summary>같은 이름의 변형(이름_1.._n) 가운데 하나.</summary>
        public static void PlayVariant(string name, int count, float volume = 0.5f)
        {
            if (!inst) return;
            var c = inst.Get(name + "_" + Random.Range(1, count + 1));
            if (!c || c.name.StartsWith("synth")) return;
            inst.sfx.pitch = Random.Range(0.94f, 1.06f);
            inst.sfx.PlayOneShot(c, volume);
        }

        /// <summary>배경 음악을 천천히 바꿔 튼다(Resources/Audio/music_*). 없으면 아무것도 안 함.</summary>
        public static void Music(string name, float volume = 0.38f)
        {
            if (!inst || inst.currentMusic == name) return;
            inst.currentMusic = name;
            inst.musicBase = volume;
            var clip = string.IsNullOrEmpty(name) ? null : Resources.Load<AudioClip>("Audio/" + name);
            if (inst.musicFade != null) inst.StopCoroutine(inst.musicFade);   // 음악만 멈춤(환경음 바꿈은 그대로)
            inst.musicFade = inst.StartCoroutine(inst.Crossfade(clip, volume));
        }

        System.Collections.IEnumerator Crossfade(AudioClip clip, float volume)
        {
            var from = musicA.isPlaying ? musicA : musicB;
            var to = from == musicA ? musicB : musicA;
            fading = true;
            volume *= Mathf.Clamp01(GameSettings.MusicVolume);
            if (clip) { to.clip = clip; to.volume = 0; to.Play(); }
            float t = 0, v0 = from.volume;
            while (t < 1f)
            {
                t += Time.unscaledDeltaTime / 2.5f;
                from.volume = Mathf.Lerp(v0, 0, t);
                if (clip) to.volume = Mathf.Lerp(0, volume, t);
                yield return null;
            }
            from.Stop();
            fading = false;
        }

        /// <summary>구역마다 바탕 소리를 바꿈(Resources/Audio/amb_*, 없으면 ambient). 1.5초 동안 갈아 끼움.</summary>
        public static void Ambient(string name)
        {
            if (!inst || string.IsNullOrEmpty(name) || inst.currentAmb == name) return;
            var c = inst.Get(name) ?? inst.Get("ambient");
            if (!c) return;
            inst.currentAmb = name;
            if (inst.ambFade != null) inst.StopCoroutine(inst.ambFade);
            inst.ambFade = inst.StartCoroutine(inst.SwapAmb(c));
        }

        System.Collections.IEnumerator SwapAmb(AudioClip c)
        {
            float target = AmbBase * Mathf.Clamp01(GameSettings.AmbientVolume), v0 = amb.volume, t = 0;
            while (t < 1f) { t += Time.unscaledDeltaTime / 0.75f; amb.volume = Mathf.Lerp(v0, 0, t); yield return null; }
            amb.clip = c; amb.Play(); t = 0;
            while (t < 1f) { t += Time.unscaledDeltaTime / 0.75f; amb.volume = Mathf.Lerp(0, target, t); yield return null; }
        }

        /// <summary>이름 붙은 반복 소리(웅성임·무거운 수레·달리기 등). follow를 주면 그 물체를 따라 3D로.</summary>
        public static void Loop(string key, string name, float volume = 0.5f, Transform follow = null)
        {
            if (!inst) return;
            var c = inst.Get(name); if (!c) return;
            if (!inst.loops.TryGetValue(key, out var src) || !src)
            {
                var go = new GameObject("Loop_" + key);
                go.transform.SetParent(follow ? follow : inst.transform, false);
                src = go.AddComponent<AudioSource>(); src.loop = true; src.playOnAwake = false;
                src.spatialBlend = follow ? 0.85f : 0f; src.minDistance = 3f; src.maxDistance = 30f;
                inst.loops[key] = src;
            }
            src.clip = c; src.volume = volume * Mathf.Clamp01(GameSettings.SfxVolume);
            if (!src.isPlaying) src.Play();
        }

        public static void StopLoop(string key, float fade = 0.6f)
        {
            if (!inst || !inst.loops.TryGetValue(key, out var src) || !src) return;
            inst.StartCoroutine(inst.FadeOutLoop(src, fade));
        }

        System.Collections.IEnumerator FadeOutLoop(AudioSource s, float secs)
        {
            float v0 = s.volume, t = 0;
            while (t < 1f && s) { t += Time.unscaledDeltaTime / Mathf.Max(0.01f, secs); s.volume = Mathf.Lerp(v0, 0, t); yield return null; }
            if (s) s.Stop();
        }

        public static void Play(string name, float volume = 0.7f, float pitch = 1f)
        {
            if (!inst) return;
            var c = inst.Get(name);
            if (!c) return;
            inst.sfx.pitch = pitch * Random.Range(0.96f, 1.04f);
            inst.sfx.PlayOneShot(c, volume);
        }

        AudioClip Get(string name)
        {
            if (clips.TryGetValue(name, out var c)) return c;
            c = Resources.Load<AudioClip>("Audio/" + name);
            if (!c && name.Contains("_") && char.IsDigit(name[name.Length - 1])) { clips[name] = null; return null; }
            if (!c) c = Synth(name);
            clips[name] = c;
            return c;
        }

        static AudioClip Synth(string name)
        {
            switch (name)
            {
                case "piece": return Make(name, 0.09f, (t, i) => Tone(t, 820, 0.012f) * 0.6f + Noise(i) * Env(t, 0.004f, 0.03f) * 0.35f);
                case "drop": return Make(name, 0.14f, (t, i) => Tone(t, 520, 0.03f) * 0.55f + Noise(i) * Env(t, 0.003f, 0.05f) * 0.3f);
                case "latch": return Make(name, 0.35f, (t, i) => (Tone(t, 1900, 0.02f) + Tone(t - 0.12f, 1300, 0.03f) * 0.8f) * 0.45f + Noise(i) * Env(t, 0.002f, 0.08f) * 0.25f);
                case "confirm": return Make(name, 1.4f, (t, i) => (Tone(t, 660, 0.9f) + Tone(t - 0.09f, 990, 0.8f) * 0.7f + Tone(t - 0.18f, 1320, 0.7f) * 0.5f) * 0.32f);
                case "speak": return Make(name, 0.6f, (t, i) => Mathf.Sin(2 * Mathf.PI * (180 + 60 * Mathf.Sin(t * 22)) * t) * Env(t, 0.03f, 0.45f) * 0.35f);
                case "wrong": return Make(name, 0.5f, (t, i) => Mathf.Sin(2 * Mathf.PI * (140 - 60 * t) * t) * Env(t, 0.01f, 0.4f) * 0.5f);
                case "page": return Make(name, 0.45f, (t, i) => Noise(i) * Env(t, 0.05f, 0.35f) * (0.4f + 0.3f * Mathf.Sin(t * 40)));
                case "almost": return Make(name, 0.7f, (t, i) => (Tone(t, 523, 0.5f) + Tone(t - 0.14f, 494, 0.5f)) * 0.3f);
                case "fish": return Make(name, 2.6f, (t, i) => (Mathf.Sin(2 * Mathf.PI * (55 + 30 * t) * t) * 0.6f + Noise(i) * 0.4f) * Env(t, 0.2f, 2.2f));
                case "ambient": return Make(name, 8f, (t, i) => Ambient(t, i), loopable: true);
                default: return null;
            }
        }

        static float Env(float t, float a, float d) => t < 0 ? 0 : t < a ? t / a : Mathf.Exp(-(t - a) / Mathf.Max(0.001f, d) * 3f);
        static float Tone(float t, float f, float d) => t < 0 ? 0 : Mathf.Sin(2 * Mathf.PI * f * t) * Env(t, 0.003f, d);
        static uint seed = 22222;
        static float Noise(int i) { seed = seed * 1664525u + 1013904223u; return ((seed >> 9) / (float)(1 << 23)) * 2f - 1f; }
        static float lp;
        static float Ambient(float t, int i)
        {
            // 동굴 바람: 걸러 낸 잡음이 천천히 숨쉰다 + 아주 낮은 웅웅거림
            lp += (Noise(i) - lp) * 0.012f;
            float swell = 0.55f + 0.45f * Mathf.Sin(2 * Mathf.PI * t / 8f);
            return lp * 2.2f * swell + Mathf.Sin(2 * Mathf.PI * 46 * t) * 0.04f;
        }

        static AudioClip Make(string name, float seconds, System.Func<float, int, float> f, bool loopable = false)
        {
            int n = Mathf.CeilToInt(seconds * Rate);
            var data = new float[n];
            for (int i = 0; i < n; i++) data[i] = Mathf.Clamp(f(i / (float)Rate, i), -1f, 1f);
            if (loopable)
            {
                int fade = Rate / 2;
                for (int i = 0; i < fade; i++) { float k = i / (float)fade; data[i] = data[i] * k + data[n - fade + i] * (1 - k); }
            }
            var clip = AudioClip.Create(name, n, 1, Rate, false);
            clip.SetData(data, 0);
            return clip;
        }
    }
}
