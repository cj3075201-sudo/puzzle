using System;
using System.Collections;
using OUAT.Core;
using UnityEngine;

namespace OUAT.World
{
    /// <summary>
    /// 먹물 웅덩이 밑의 물고기 = 왕의 배달꾼(설계 초안 10/23). 막오름 날에만 솟아 바친 것을 삼키고, 덩어리와 왕의 띠를 뱉고 가라앉는다.
    /// 블렌더 클립(Hidden·Rise·Idle·OpenMouth·Swallow·Spit·Sink, 원점 = 웅덩이 수면 가운데)이 있으면 그것으로, 없으면 옛 절차 움직임.
    /// </summary>
    public class FishActor : MonoBehaviour
    {
        public Transform model;
        public Transform jawUpper, jawLower;
        public float hiddenDepth = -11f;
        public Transform cartItemsRoot;
        public ParticleSystem splash;

        Vector3 restPos;
        Animation anim;

        void Awake()
        {
            if (!model) model = transform.childCount > 0 ? transform.GetChild(0) : transform;
            foreach (var t in GetComponentsInChildren<Transform>(true))
            {
                if (!jawUpper && t.name.Contains("JawUpper")) jawUpper = t;
                if (!jawLower && t.name.Contains("JawLower")) jawLower = t;
            }
            anim = GetComponentInChildren<Animation>(true);
            if (anim != null && anim.GetClipCount() == 0) anim = null;
            restPos = model.localPosition;
            if (anim)
            {
                foreach (AnimationState s in anim) s.wrapMode = s.name == "Hidden" || s.name == "Idle" ? WrapMode.Loop : WrapMode.ClampForever;
                anim.playAutomatically = false;
                foreach (var smr in GetComponentsInChildren<SkinnedMeshRenderer>(true)) smr.updateWhenOffscreen = true;
            }
            else model.localPosition = restPos + Vector3.up * hiddenDepth;
            model.gameObject.SetActive(false);
        }

        bool Has(string c) => anim != null && anim[c] != null;
        float Len(string c) => Has(c) ? anim[c].length : 0f;

        IEnumerator Clip(string c, float fade = 0.15f, Action at = null, float atTime = -1f)
        {
            if (!Has(c)) yield break;
            anim.CrossFade(c, fade);
            anim[c].time = 0f;
            float t = 0, len = Len(c); bool fired = false;
            while (t < len) { t += Time.deltaTime; if (!fired && at != null && t >= atTime) { fired = true; at(); } yield return null; }
            if (!fired) at?.Invoke();
        }

        IEnumerator RiseUp()
        {
            model.gameObject.SetActive(true);
            AudioHub.Play("fish_rise", 0.9f);
            if (splash) splash.Play();
            if (Has("Hidden")) anim.Play("Hidden");
            yield return Clip("Rise", 0.05f);
            AudioHub.Play("splash", 0.8f);
            if (Has("Idle")) anim.CrossFade("Idle", 0.2f);
        }

        IEnumerator SinkDown()
        {
            if (splash) splash.Play();
            AudioHub.Play("fish_sink", 0.8f);
            yield return Clip("Sink");
            model.gameObject.SetActive(false);
        }

        /// <summary>바친 물건을 삼킴(밭 끝 수레). spit이 있으면 그 전에 덩어리·띠를 뱉음(0.5초 지점).</summary>
        public IEnumerator Burst(bool takeCartItems, Action spit = null)
        {
            if (!anim) { yield return OldBurst(takeCartItems); spit?.Invoke(); yield break; }
            yield return RiseUp();
            yield return new WaitForSeconds(0.6f);
            if (spit != null) { yield return Clip("Spit", 0.15f, spit, 0.5f); yield return new WaitForSeconds(0.5f); }   // 뱉는 소리(fish_spit)는 장면이 냄
            AudioHub.Play("fish_open", 0.8f);
            yield return Clip("OpenMouth");
            yield return Clip("Swallow", 0.1f, () => { if (takeCartItems && cartItemsRoot) cartItemsRoot.gameObject.SetActive(false); AudioHub.Play("fish_gulp", 0.9f); }, 0.25f);
            yield return new WaitForSeconds(0.4f);
            yield return SinkDown();
        }

        /// <summary>막오름 날: 나와 키노피오를 함께 삼킴 → 2챕터.</summary>
        public IEnumerator Swallow(Transform hero, Transform kid)
        {
            if (!anim) { yield return OldSwallow(hero, kid); yield break; }
            yield return RiseUp();
            AudioHub.Play("fish_open", 0.9f);
            yield return Clip("OpenMouth");
            yield return new WaitForSeconds(0.8f);
            yield return Clip("Swallow", 0.1f, () =>
            {
                if (hero) foreach (var r in hero.GetComponentsInChildren<Renderer>()) r.enabled = false;
                if (kid) foreach (var r in kid.GetComponentsInChildren<Renderer>()) r.enabled = false;
                AudioHub.Play("fish_gulp", 1f, 0.85f);
            }, 0.2f);
            yield return new WaitForSeconds(0.9f);
            yield return SinkDown();
        }

        // ── 클립이 없을 때(옛 모형) ──
        IEnumerator Move(float fromY, float toY, float seconds, float ease = 3f)
        {
            float t = 0;
            while (t < 1f)
            {
                t += Time.deltaTime / seconds;
                float k = 1f - Mathf.Pow(1f - Mathf.Clamp01(t), ease);
                model.localPosition = restPos + Vector3.up * Mathf.LerpUnclamped(fromY, toY, k);
                yield return null;
            }
        }

        IEnumerator Jaw(float open, float seconds)
        {
            float t = 0;
            var u0 = jawUpper ? jawUpper.localRotation : Quaternion.identity;
            var l0 = jawLower ? jawLower.localRotation : Quaternion.identity;
            while (t < 1f)
            {
                t += Time.deltaTime / seconds;
                float k = Mathf.SmoothStep(0, 1, t);
                if (jawUpper) jawUpper.localRotation = Quaternion.Slerp(u0, Quaternion.Euler(-open * 0.6f, 0, 0), k);
                if (jawLower) jawLower.localRotation = Quaternion.Slerp(l0, Quaternion.Euler(open, 0, 0), k);
                yield return null;
            }
        }

        IEnumerator OldBurst(bool takeCartItems)
        {
            model.gameObject.SetActive(true);
            AudioHub.Play("fish", 0.9f);
            if (splash) splash.Play();
            StartCoroutine(Jaw(38f, 0.6f));
            yield return Move(hiddenDepth, 1.5f, 0.9f, 4f);
            AudioHub.Play("splash", 0.8f);
            if (takeCartItems && cartItemsRoot) cartItemsRoot.gameObject.SetActive(false);
            yield return Jaw(0f, 0.25f);
            yield return new WaitForSeconds(0.5f);
            if (splash) splash.Play();
            yield return Move(1.5f, hiddenDepth, 1.4f, 2f);
            model.gameObject.SetActive(false);
        }

        IEnumerator OldSwallow(Transform hero, Transform kid)
        {
            model.gameObject.SetActive(true);
            AudioHub.Play("fish", 1f, 0.85f);
            if (splash) splash.Play();
            StartCoroutine(Jaw(55f, 0.5f));
            yield return Move(hiddenDepth, 2.2f, 0.8f, 4f);
            yield return Jaw(0f, 0.22f);
            if (hero) foreach (var r in hero.GetComponentsInChildren<Renderer>()) r.enabled = false;
            if (kid) foreach (var r in kid.GetComponentsInChildren<Renderer>()) r.enabled = false;
            yield return new WaitForSeconds(0.9f);
            if (splash) splash.Play();
            yield return Move(2.2f, hiddenDepth, 1.8f, 2f);
            model.gameObject.SetActive(false);
        }
    }
}
