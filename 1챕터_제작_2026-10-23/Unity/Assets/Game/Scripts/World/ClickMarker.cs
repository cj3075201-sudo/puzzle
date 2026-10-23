using UnityEngine;

namespace OUAT.World
{
    /// <summary>클릭한 자리에 잠깐 남는 잉크 동그라미.</summary>
    public class ClickMarker : MonoBehaviour
    {
        Renderer[] rends;
        float t = 1f;
        void Awake() { rends = GetComponentsInChildren<Renderer>(); SetVisible(false); }
        public void Show(Vector3 p) { transform.position = p + Vector3.up * 0.03f; t = 0f; SetVisible(true); }
        void Update()
        {
            if (t >= 1f) return;
            t += Time.deltaTime * 1.6f;
            float s = Mathf.Lerp(0.5f, 1.1f, Mathf.Sqrt(t));
            transform.localScale = new Vector3(s, 1, s);
            if (t >= 1f) SetVisible(false);
        }
        void SetVisible(bool v) { foreach (var r in rends) r.enabled = v; }
    }
}
