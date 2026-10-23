using UnityEngine;

namespace OUAT.World
{
    /// <summary>먹물 웅덩이 수면. 평소 마른 먹처럼 고요, 데려가지는 날엔 먹물 고리가 천천히 돈다.</summary>
    public class PondSurface : MonoBehaviour
    {
        public bool awake;
        Vector3 baseScale;
        float t;
        void Awake() { baseScale = transform.localScale; }
        public void SetAwake(bool on) { awake = on; }
        public void Bulge(float amount) { t = amount; }
        void Update()
        {
            if (awake) transform.Rotate(0, Time.deltaTime * 8f, 0, Space.Self);
            t = Mathf.MoveTowards(t, 0f, Time.deltaTime * 0.8f);
            float b = 1f + (awake ? 0.01f * Mathf.Sin(Time.time * 1.3f) : 0f);
            transform.localScale = new Vector3(baseScale.x * b, baseScale.y * (1f + t * 6f), baseScale.z * b);
        }
    }
}
