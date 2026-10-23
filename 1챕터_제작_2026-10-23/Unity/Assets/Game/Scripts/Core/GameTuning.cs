using UnityEngine;

namespace OUAT.Core
{
    /// <summary>
    /// 사용자가 직접 바꿔 보는 수치(직-13·14, 화-10). Assets/Game/Resources/OUAT_Tuning.asset 을 인스펙터에서 고치면 바로 반영된다.
    /// </summary>
    [CreateAssetMenu(menuName = "OUAT/Tuning", fileName = "OUAT_Tuning")]
    public class GameTuning : ScriptableObject
    {
        [Header("직소 조립판")]
        [Tooltip("조립판 한 칸 크기(px, 1920×1080 기준)")] public float cellSize = 104f;
        [Tooltip("0보다 크면 모든 대화의 조립판 가로 칸 수를 이 값으로")] public int boardWidthOverride = 0;
        [Tooltip("0보다 크면 모든 대화의 조립판 세로 칸 수를 이 값으로")] public int boardHeightOverride = 0;
        [Tooltip("데이터에 판 크기가 없을 때")] public Vector2Int defaultBoard = new Vector2Int(5, 3);
        [Tooltip("대화마다 데이터 모형에 더해 꺼내 줄 모형 수(헷갈리게 하는 여분)")] public int extraModels = 0;
        [Tooltip("모형 하나를 몇 번까지 꺼내 쓸 수 있나(0 = 제한 없음)")] public int modelUses = 0;
        [Tooltip("판에 놓을 수 있는 조각 최대 수(0 = 제한 없음)")] public int pieceLimit = 0;
        [Tooltip("크리처 말(읽기 판) 칸 크기 배율")] public float readBoardScale = 0.62f;
        [Tooltip("머리 위 말 배율")] public float overheadScale = 0.5f;

        [Header("카메라 (플레이어는 조종 못 함)")]
        public float cameraYaw = 35f;
        public float cameraPitch = 38f;
        public float cameraDistance = 15f;
        public float cameraFov = 32f;
        [Tooltip("따라가는 부드러움(초)")] public float cameraFollowTime = 0.35f;

        [Header("이동")]
        public float walkSpeed = 3.2f;

        [Header("뜻 추측")]
        [Tooltip("새김 문장이 몇 글자 이상일 때 '거의 맞음'을 보여 줄지")] public int almostMinGlyphs = 4;

        static GameTuning cached;
        public static GameTuning Get()
        {
            if (cached) return cached;
            cached = Resources.Load<GameTuning>("OUAT_Tuning");
            if (!cached) cached = CreateInstance<GameTuning>();
            return cached;
        }
    }
}
