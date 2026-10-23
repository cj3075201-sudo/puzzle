using System.Collections.Generic;
using UnityEngine;

namespace OUAT.World
{
    /// <summary>
    /// 플레이어가 조종하지 못하는 고정 각도 카메라(화-10, 세나르처럼). 주인공을 부드럽게 따라가고,
    /// 구역(CameraZone)에 들어가면 그 구역의 각도·거리로 천천히 바뀐다. 연출 중에는 Focus로 잠시 다른 곳을 본다.
    /// </summary>
    public class FollowCamera : MonoBehaviour
    {
        [System.Serializable]
        public struct View
        {
            public float yaw, pitch, distance, fov;
            public Vector3 offset;
            public static View Default => new View { yaw = 35f, pitch = 38f, distance = 15f, fov = 32f, offset = new Vector3(0, 0.6f, 0) };
            public static View Lerp(View a, View b, float t) => new View
            {
                yaw = Mathf.LerpAngle(a.yaw, b.yaw, t), pitch = Mathf.Lerp(a.pitch, b.pitch, t),
                distance = Mathf.Lerp(a.distance, b.distance, t), fov = Mathf.Lerp(a.fov, b.fov, t),
                offset = Vector3.Lerp(a.offset, b.offset, t)
            };
        }

        public Transform target;
        public float CurrentYaw => current.yaw;
        public View baseView = View.Default;
        [Tooltip("따라가는 부드러움(초)")] public float followTime = 0.35f;
        [Tooltip("구역 바뀔 때 각도가 넘어가는 시간(초)")] public float zoneBlendTime = 1.6f;

        Camera cam;
        View current, from, to;
        float blendT = 1f;
        Vector3 pivot, pivotVel;
        readonly List<CameraZone> zones = new List<CameraZone>();
        Vector3? focusPoint; float focusWeight; View? focusView;

        void Awake()
        {
            cam = GetComponent<Camera>();
            current = from = to = baseView;
        }

        public void SnapToTarget()
        {
            if (!target) return;
            pivot = target.position;
            pivotVel = Vector3.zero;
            current = from = to = ActiveView();
            blendT = 1f;
            Apply();
        }

        public void Enter(CameraZone z) { if (!zones.Contains(z)) { zones.Add(z); Retarget(); } }
        public void Exit(CameraZone z) { if (zones.Remove(z)) Retarget(); }

        /// <summary>연출: 한 지점을 잠시 바라본다(null이면 원래대로).</summary>
        public void Focus(Vector3? point, View? view = null)
        {
            if (point.HasValue) { focusPoint = point; focusView = view; lastFocusPoint = point.Value; lastFocusView = view; }
            else focusPoint = null;   // 무게가 0이 될 때까지 마지막 시점을 유지해 툭 끊기지 않게(QA P2-17)
        }
        Vector3 lastFocusPoint; View? lastFocusView;

        View ActiveView()
        {
            CameraZone best = null;
            foreach (var z in zones) if (z && (best == null || z.priority > best.priority)) best = z;
            return best ? best.view : baseView;
        }

        void Retarget() { from = current; to = ActiveView(); blendT = 0f; }

        void LateUpdate()
        {
            if (!target) return;
            float targetW = focusPoint.HasValue ? 1f : 0f;
            focusWeight = Mathf.MoveTowards(focusWeight, targetW, Time.deltaTime * 0.9f);
            if (!focusPoint.HasValue && focusWeight <= 0f) focusView = null;
            Vector3 goal = Vector3.Lerp(target.position, focusPoint ?? lastFocusPoint, Smooth(focusWeight));
            if (bounds.HasValue && !focusPoint.HasValue)
            {
                var b = bounds.Value; float m = 4f;
                goal.x = Mathf.Clamp(goal.x, b.xMin + m, Mathf.Max(b.xMin + m, b.xMax - m));
                goal.z = Mathf.Clamp(goal.z, b.yMin + m, Mathf.Max(b.yMin + m, b.yMax - m));
            }
            pivot = Vector3.SmoothDamp(pivot, goal, ref pivotVel, followTime);

            if (blendT < 1f) blendT = Mathf.Min(1f, blendT + Time.deltaTime / zoneBlendTime);
            current = View.Lerp(from, to, Smooth(blendT));
            var fv = focusPoint.HasValue ? focusView : lastFocusView;
            // 연출 시점끼리 옮겨 갈 때도 각도·거리가 툭 바뀌지 않게 부드럽게(내려다보기→올려다보기 등)
            if (fv.HasValue) fvSmooth = fvSmooth.HasValue && focusWeight > 0f ? View.Lerp(fvSmooth.Value, fv.Value, 1f - Mathf.Exp(-Time.deltaTime * viewLerp)) : fv;
            if (fvSmooth.HasValue && focusWeight > 0f) current = View.Lerp(current, fvSmooth.Value, Smooth(focusWeight));
            Apply();
        }

        View? fvSmooth;
        public float viewLerp = 2.2f;

        /// <summary>연출 첫 시점으로 곧장(페이드 뒤 등): 부드럽게 옮겨 가지 않고 바로 그 자리.</summary>
        public void SnapFocus()
        {
            if (!focusPoint.HasValue) return;
            focusWeight = 1f; pivot = focusPoint.Value; pivotVel = Vector3.zero; fvSmooth = focusView;
            if (focusView.HasValue) current = focusView.Value;
            Apply();
        }

        Rect? bounds;
        /// <summary>구역 안에서만 따라가게(가장자리 너머 다른 구역이 보이지 않게).</summary>
        public void SetBounds(Rect r) { bounds = r.width > 0 ? r : (Rect?)null; }

        float shake;
        public void Shake(float seconds) { if (!OUAT.Core.GameSettings.ScreenShake) return; shake = Mathf.Max(shake, seconds); }

        void Apply()
        {
            var rot = Quaternion.Euler(current.pitch, current.yaw, 0);
            var look = pivot + current.offset;
            if (shake > 0f) { shake -= Time.deltaTime; look += Random.insideUnitSphere * 0.08f * Mathf.Clamp01(shake * 4f); }
            transform.position = look - rot * Vector3.forward * current.distance;
            transform.rotation = rot;
            if (cam) cam.fieldOfView = current.fov;
        }

        static float Smooth(float x) => x * x * (3f - 2f * x);
    }
}
