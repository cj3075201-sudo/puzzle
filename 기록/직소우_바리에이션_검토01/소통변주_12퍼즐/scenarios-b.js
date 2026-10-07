(() => {
  'use strict';
  const eq = (tree, spec) => globalThis.JigsawCore.eq(tree, spec);
  const result = (state, ok, message, changes = {}, speech) => ({ state: { ...state, ...changes }, ok, message, ...(speech ? { speech } : {}) });
  const actor = (id, label, role, x, speech = [], color = '#e4c369') => ({ id, label, role, color, x, speech });
  const inspect = (messages, speeches = {}) => (id, state) => result(state, false, messages[id] || '들을 상대를 골라 주세요.', {}, speeches[id]);
  const items = [
    {
      id: 7, title: '질문 조각은 어디에?', theme: '진료소의 빠진 정보', experimental: true,
      goal: '안내인에게 환자 이름과 아픈 부위를 알아내고, 의사에게 정확히 전하세요.',
      intro: '안내인은 손이 차가운 주민 한 명을 봤습니다. 의사는 그 주민의 아픈 곳을 알아야 치료를 준비할 수 있습니다.',
      rule: '파랑 질문은 모르는 자리에 놓습니다. 예: 질문→손→차갑다는 누구의 손인지, 수리→질문→아프다는 어느 부위인지 묻습니다.',
      words: ['질문', '손', '차갑다', '수리', '발', '아프다'], blueWords: ['질문', '차갑다', '아프다'],
      hint: ['먼저 손이 차갑다는 조건은 남기고, 모르는 사람 자리를 질문으로 만드세요.', '이름을 알면 질문을 그 주민의 신체 부위 자리로 옮기세요. 마지막 보고에는 질문이 필요 없습니다.'],
      actors: [actor('guide', '안내인', '누가 어디가 아픈지 보았습니다', 28, [['손', '차갑다']]), actor('doctor', '의사', '환자의 아픈 부위를 기다립니다', 74)],
      initial: { named: false, located: false, complete: false },
      inspect: inspect({ guide: '손이 차가운 사람이 한 명 있어요. 누구인지도, 어디가 아픈지도 물어보면 알려드릴게요.', doctor: '환자 이름과 아픈 부위를 함께 알려 주세요.' }),
      submit(tree, s, listener) {
        if (listener === 'guide' && eq(tree, ['질문', ['손', '차갑다']])) return result(s, true, '안내인: 손이 차가운 사람은 수리예요. 하지만 차가운 손이 아픈 곳인지는 아직 모르죠.', { named: true }, [['수리', ['손', '차갑다']]]);
        if (listener === 'guide' && eq(tree, ['수리', ['질문', '아프다']])) return result(s, true, '안내인: 수리는 발이 아파요. 손은 차갑기만 해요.', { located: true }, [['수리', ['발', '아프다']]]);
        if (listener === 'doctor' && eq(tree, ['수리', ['발', '아프다']])) return result(s, true, '의사: 수리의 발을 치료할 준비가 됐어요.', { complete: true });
        if (listener === 'doctor' && eq(tree, ['수리', ['손', '아프다']])) return result(s, false, '의사: 수리는 손이 아프지 않대요. 차가운 부위와 아픈 부위를 구별해 주세요.');
        return result(s, false, listener === 'guide' ? '안내인: 누구인지 묻는 건가요, 어느 부위인지 묻는 건가요? 질문이 붙는 자리를 살펴보세요.' : '의사: 질문 대신 환자 이름에 아픈 부위를 연결해 알려 주세요.');
      },
      solutions: [{ listener: 'guide', spec: ['질문', ['손', '차갑다']] }, { listener: 'guide', spec: ['수리', ['질문', '아프다']] }, { listener: 'doctor', spec: ['수리', ['발', '아프다']] }]
    },
    {
      id: 8, title: '무엇이 아닌가?', theme: '추운 다리 앞', experimental: true,
      goal: '손이 차갑지 않은 주민을 진료소로 보내고, 손이 차가운 주민은 다리로 가지 않게 하세요.',
      intro: '손이 차가운 주민은 추운 다리에서 상태가 나빠집니다. 관리인에게 두 주민의 이동을 서로 다르게 부탁하세요.',
      rule: '파랑 아니다는 바로 아래 표현을 부정합니다. 예: 아니다→차갑다는 차갑지 않음, 아니다→가다는 가지 않음입니다.',
      words: ['가다', '아니다', '주민', '손', '차갑다', '진료소', '다리'], blueWords: ['가다', '아니다', '차갑다'],
      hint: ['진료소에 갈 사람을 고를 때는 손의 차가움을 부정하세요. 이동은 긍정으로 남깁니다.', '다리로 가지 않게 할 때는 차가운 상태를 그대로 두고, 가다 전체를 부정하세요.'],
      actors: [actor('manager', '관리인', '두 주민의 이동을 맡습니다', 50, [['주민', ['손', '차갑다']], ['주민', ['손', ['아니다', '차갑다']]]])],
      initial: { warmSent: false, coldStopped: false, complete: false },
      inspect: inspect({ manager: '오른쪽 주민은 손이 차갑고, 왼쪽 주민은 차갑지 않아요. 따뜻한 손의 주민은 진료소에 갈 수 있고, 차가운 손의 주민은 다리를 피해야 해요.' }),
      submit(tree, s, listener) {
        if (listener !== 'manager') return result(s, false, '이동을 맡은 관리인에게 말해 주세요.');
        if (eq(tree, ['주민', ['손', ['아니다', '차갑다']], ['가다', '진료소']])) return result(s, true, '손이 차갑지 않은 주민이 진료소로 갔습니다.', { warmSent: true, complete: !!s.coldStopped });
        if (eq(tree, ['주민', ['손', '차갑다'], ['아니다', ['가다', '다리']]])) return result(s, true, '관리인: 손이 차가운 주민은 다리로 보내지 않을게요.', { coldStopped: true, complete: !!s.warmSent });
        if (eq(tree, ['주민', ['손', '차갑다'], ['가다', '다리']])) return result(s, false, '관리인: 이 말은 손이 차가운 주민을 다리로 보내라는 뜻이에요. 상태가 더 나빠질 수 있어 실행하지 않았어요.');
        if (eq(tree, ['주민', ['손', '차갑다'], ['아니다', ['가다', '진료소']]])) return result(s, false, '관리인: 이것은 진료소로 가는 행동을 막는 말이에요. 차갑지 않은 사람을 고르는 말과 달라요.');
        return result(s, false, '관리인: 아니다가 사람을 고르는 상태에 붙었는지, 이동에 붙었는지 확인해 주세요.');
      },
      solutions: [{ listener: 'manager', spec: ['주민', ['손', ['아니다', '차갑다']], ['가다', '진료소']] }, { listener: 'manager', spec: ['주민', ['손', '차갑다'], ['아니다', ['가다', '다리']]] }]
    },
    {
      id: 9, title: '언제 아픈가?', theme: '같은 통증, 다른 도움', experimental: true,
      goal: '수리와 모루의 통증 조건을 의사에게 전달해, 각자 다른 처치를 받게 하세요.',
      intro: '두 주민 모두 손이 아프지만 원인이 다릅니다. 의사는 조건을 알면 고정대와 보온 장갑 중 알맞은 처치를 고릅니다.',
      rule: '결과 상태에 파랑 때를 붙이고, 때 아래에 조건을 넣습니다. 예: 아프다에 때→움직이다가 붙으면 움직일 때 아프다는 뜻입니다.',
      words: ['수리', '모루', '손', '움직이다', '차갑다', '아프다', '때'], blueWords: ['움직이다', '차갑다', '아프다', '때'],
      hint: ['수리는 움직임이 조건이고 통증이 결과입니다. 모루는 차가움이 조건입니다.', '주민→손→아프다를 잇고, 아프다 뒤에 때를 붙이세요. 때 아래 손→움직이다 또는 손→차갑다를 연결합니다.'],
      actors: [actor('suri', '수리', '가만히 있을 때는 괜찮습니다', 18, [['손', '움직이다']]), actor('moru', '모루', '따뜻할 때는 괜찮습니다', 50, [['손', '차갑다']]), actor('doctor', '의사', '조건에 따라 처치를 고릅니다', 82)],
      initial: { splint: false, mitten: false, complete: false },
      inspect: inspect({ suri: '수리: 가만히 두면 괜찮아요. 손을 움직이면 아파요. 따뜻해도 움직이면 아파요.', moru: '모루: 손이 차가워지면 아파요. 따뜻할 때는 움직여도 괜찮아요.', doctor: '움직일 때 아프면 고정대, 차가울 때 아프면 보온 장갑이 필요해요. 누구에게 어느 조건인지 알려 주세요.' }),
      submit(tree, s, listener) {
        if (listener !== 'doctor') return result(s, false, '주민: 제 경험은 알려드렸어요. 처치는 의사에게 부탁해 주세요.');
        if (eq(tree, ['수리', ['손', ['아프다', ['때', ['손', '움직이다']]]]])) return result(s, true, '의사: 수리는 움직임을 줄이는 고정대를 쓰면 되겠어요.', { splint: true, complete: !!s.mitten });
        if (eq(tree, ['모루', ['손', ['아프다', ['때', ['손', '차갑다']]]]])) return result(s, true, '의사: 모루에게는 보온 장갑을 줄게요.', { mitten: true, complete: !!s.splint });
        if (eq(tree, ['수리', ['손', ['움직이다', ['때', ['손', '아프다']]]]])) return result(s, false, '의사: 이 순서는 아프면 움직인다는 뜻이에요. 수리는 움직일 때 아픈 거예요.');
        if (eq(tree, ['모루', ['손', ['아프다', ['때', ['손', '움직이다']]]]])) return result(s, false, '의사: 모루는 따뜻하면 움직여도 괜찮다 했어요. 조건을 다시 연결해 주세요.');
        return result(s, false, '의사: 손이 아프다는 정보만으로는 처치를 고를 수 없어요. 누구의 손이 어떤 조건에서 아픈지 연결해 주세요.');
      },
      solutions: [{ listener: 'doctor', spec: ['수리', ['손', ['아프다', ['때', ['손', '움직이다']]]]] }, { listener: 'doctor', spec: ['모루', ['손', ['아프다', ['때', ['손', '차갑다']]]]] }]
    },
    {
      id: 10, title: '그때 열린 문, 지금 열린 문', theme: '바뀐 통로', experimental: true,
      goal: '현재 통로를 확인하고, 짐꾼에게 지금 이용할 수 있는 문을 알려 주세요.',
      intro: '여행자는 어제 서문을 통과했습니다. 오늘 폭우로 서문이 닫혔고, 경비원은 현재 우회로를 알고 있습니다.',
      rule: '파랑 이전과 지금은 아래 발화의 시점을 정합니다. 예: 질문→지금→길은 현재 길을, 질문→이전→길은 과거 길을 묻습니다.',
      words: ['질문', '지금', '이전', '길', '서문', '동문', '열리다', '닫히다'], blueWords: ['질문', '지금', '이전', '열리다', '닫히다'],
      hint: ['여행자의 이전 정보는 오늘 길을 보장하지 않아요. 경비원에게 현재 길을 물으세요.', '경비원의 응답에서 지금 쓸 수 있는 문을 골라, 짐꾼에게 현재 시점으로 전하세요.'],
      actors: [actor('traveler', '여행자', '어제 도착했습니다', 18, [['이전', ['서문', '열리다']]]), actor('guard', '경비원', '오늘 길을 점검했습니다', 50, [['지금', ['서문', '닫히다']]]), actor('porter', '짐꾼', '오늘 통과할 길이 필요합니다', 82)],
      initial: { learnedNow: false, complete: false },
      inspect: inspect({ traveler: '어제는 서문이 열려 있었어요. 오늘은 가보지 못했어요.', guard: '오늘 서문은 닫혔어요. 이전 상황과 지금 갈 수 있는 길 중 어느 쪽이 궁금한가요?', porter: '짐을 싣고 지금 통과할 수 있는 문을 알려 주세요.' }),
      submit(tree, s, listener) {
        if (listener === 'guard' && eq(tree, ['질문', ['지금', '길']])) return result(s, true, '경비원: 지금은 동문이 열려 있어요. 서문은 닫혀 있습니다.', { learnedNow: true }, [['지금', ['동문', '열리다']], ['지금', ['서문', '닫히다']]]);
        if (listener === 'guard' && eq(tree, ['질문', ['이전', '길']])) return result(s, true, '경비원: 어제는 서문이 열려 있었어요. 오늘 갈 길은 달라졌어요.', {}, [['이전', ['서문', '열리다']]]);
        if (listener === 'porter' && eq(tree, ['지금', ['동문', '열리다']])) return result(s, true, '짐꾼이 동문으로 가서 통과했습니다.', { complete: true });
        if (listener === 'porter' && eq(tree, ['이전', ['서문', '열리다']])) return result(s, false, '짐꾼: 어제 열린 문이라는 건 알겠어요. 지금 이용할 문이 필요해요.');
        if (listener === 'porter' && eq(tree, ['지금', ['서문', '열리다']])) return result(s, false, '짐꾼: 서문은 오늘 닫혔어요. 이전 정보를 지금으로 바꾸면 사실이 달라져요.');
        return result(s, false, '현재 길을 아는 경비원에게 시점을 담아 질문하거나, 짐꾼에게 지금 열린 문을 알려 주세요.');
      },
      solutions: [{ listener: 'guard', spec: ['질문', ['지금', '길']] }, { listener: 'porter', spec: ['지금', ['동문', '열리다']] }]
    },
    {
      id: 11, title: '누가 그렇게 말했나?', theme: '출처가 남는 전달', experimental: true,
      goal: '기록관에 소문의 출처를 남기고, 문지기에게 현재 상태를 확인해 탐험가에게 전하세요.',
      intro: '전령은 문지기가 문이 안전하다고 말했다고 전합니다. 기록관은 발언 기록을, 탐험가는 지금 사실을 원합니다.',
      rule: '파랑 말하다에 발언자 낱개와 내용 조립을 붙입니다. 예: 말하다에 문지기와 문→안전하다를 붙이면 문지기의 발언을 인용합니다.',
      words: ['말하다', '문지기', '문', '안전하다', '아니다', '질문', '지금'], blueWords: ['말하다', '안전하다', '아니다', '질문', '지금'],
      hint: ['기록관에게는 문 상태만 보내지 말고, 말하다에 출처와 내용을 각각 붙이세요.', '문지기에게 현재 안전한지 물어보세요. 탐험가에게는 인용이 아닌 확인한 현재 상태를 전하세요.'],
      actors: [actor('messenger', '전령', '문지기의 말을 전합니다', 12, [['말하다', '문지기', ['문', '안전하다']]]), actor('scribe', '기록관', '누가 무엇을 말했는지 기록합니다', 37), actor('guard', '문지기', '문을 직접 점검했습니다', 63), actor('explorer', '탐험가', '지금 통과해도 되는지 기다립니다', 88)],
      initial: { sourceRecorded: false, checked: false, warned: false, complete: false },
      inspect: inspect({ messenger: '문지기가 문이 안전하다고 했어요. 다만 언제 점검한 말인지는 모르겠어요.', scribe: '누가 어떤 말을 했는지 기록해야 해요. 문 상태만 말하면 출처가 사라져요.', guard: '이전에 안전하다고 말한 적 있어요. 현재 점검 결과가 필요한가요?', explorer: '현재 위험하면 들어가지 않을게요. 직접 확인된 지금 상태를 전해 주세요.' }),
      submit(tree, s, listener) {
        if (listener === 'scribe' && eq(tree, ['말하다', '문지기', ['문', '안전하다']])) return result(s, true, '기록관: 문지기가 문이 안전하다고 말한 기록을 남겼어요.', { sourceRecorded: true, complete: !!s.warned });
        if (listener === 'guard' && eq(tree, ['질문', ['지금', ['문', '안전하다']]])) return result(s, true, '문지기: 지금은 문이 안전하지 않아요. 방금 균열을 발견했어요.', { checked: true }, [['지금', ['문', ['아니다', '안전하다']]]]);
        if (listener === 'explorer' && eq(tree, ['지금', ['문', ['아니다', '안전하다']]])) return result(s, true, '탐험가: 현재 위험하군요. 통과하지 않을게요.', { warned: true, complete: !!s.sourceRecorded });
        if (listener === 'scribe' && eq(tree, ['문', '안전하다'])) return result(s, false, '기록관: 이것은 문이 안전하다는 선언이에요. 누가 말한 내용인지 남겨 주세요.');
        if (listener === 'explorer' && eq(tree, ['말하다', '문지기', ['문', '안전하다']])) return result(s, false, '탐험가: 문지기가 말했다는 건 알겠어요. 지금도 안전한지 확인이 필요해요.');
        return result(s, false, '발언 기록에는 출처와 내용이, 현재 판단에는 확인된 문 상태가 필요합니다. 듣는 사람이 원하는 정보를 구별해 주세요.');
      },
      solutions: [{ listener: 'scribe', spec: ['말하다', '문지기', ['문', '안전하다']] }, { listener: 'guard', spec: ['질문', ['지금', ['문', '안전하다']]] }, { listener: 'explorer', spec: ['지금', ['문', ['아니다', '안전하다']]] }]
    },
    {
      id: 12, title: '먼저 설 사람, 잡아 줄 사람', theme: '두 주민의 협력', experimental: true,
      goal: '두 주민이 협력해 수리가 안전하게 문을 지나도록 도와주세요.',
      intro: '두 주민이 문 앞에서 서로를 기다립니다. 발판은 이쪽에 있습니다. 각자 움직이지 못하는 이유를 듣고 건너도록 도와주세요.',
      rule: '가능한 행동에 때→조건을 붙입니다. 예: 건너다에 때→잡다가 붙으면 잡을 때 건넌다는 뜻입니다. 실행은 때 없이 부탁하며 잡기는 유지됩니다.',
      words: ['때', '수리', '모루', '발판', '문', '서다', '잡다', '건너다'], blueWords: ['때', '서다', '잡다', '건너다'],
      hint: ['문을 잡는 조건과 건너는 조건을 거꾸로 따라가세요. 가장 먼저 가능한 준비는 발판입니다.', '수리에게 발판에 서기를, 모루에게 문 잡기를, 마지막으로 수리에게 건너기를 부탁하세요.'],
      actors: [actor('suri', '수리', '건너가야 하는 주민', 28, [['수리', ['건너다', ['때', ['모루', ['잡다', '문']]]]]]), actor('moru', '모루', '문을 계속 잡을 주민', 74, [['모루', ['잡다', '문', ['때', ['수리', ['서다', '발판']]]]]])],
      initial: { onPlate: false, holding: false, crossed: false, complete: false },
      inspect(id, s) {
        if (id === 'suri') return result(s, false, s.crossed ? '수리: 무사히 건넜어요!' : s.onPlate ? '수리: 발판을 밟고 있어요. 모루가 문을 잡으면 건널 수 있어요.' : '수리: 모루가 문을 잡아 주면 건널게요. 발판은 건너기 전 이쪽에 있어요.');
        return result(s, false, s.holding ? '모루: 문을 계속 잡고 있어요. 수리는 이제 발판에서 내려와 건너도 돼요.' : '모루: 수리가 발판에 서서 문을 풀어 주면 잡을 수 있어요. 한번 잡으면 발판에서 내려와도 놓치지 않아요.');
      },
      submit(tree, s, listener) {
        if (eq(tree, ['수리', ['서다', '발판']]) && listener === 'suri') return result(s, true, '수리가 문 앞 발판에 섰습니다. 문 잠금이 풀렸습니다.', { onPlate: true });
        if (eq(tree, ['모루', ['잡다', '문']]) && listener === 'moru') {
          if (!s.onPlate) return result(s, false, '모루: 문이 잠겨 움직이지 않아요. 수리가 먼저 발판을 밟아야 해요.');
          return result(s, true, '모루가 열린 문을 단단히 잡았습니다. 이제 발판을 떠나도 문은 유지됩니다.', { holding: true });
        }
        if (eq(tree, ['수리', '건너다']) && listener === 'suri') {
          if (!s.holding) return result(s, false, '수리: 아직 모루가 문을 잡고 있지 않아요. 지금 건너면 문이 닫혀요.');
          return result(s, true, '수리가 발판에서 내려와 건넜습니다. 모루가 문을 유지해 두 주민의 조건이 해결됐습니다.', { onPlate: false, crossed: true, complete: true });
        }
        if (eq(tree, ['모루', ['잡다', '문', ['때', ['수리', ['서다', '발판']]]]]) || eq(tree, ['수리', ['건너다', ['때', ['모루', ['잡다', '문']]]]])) return result(s, true, '주민: 맞아요, 그 조건이면 가능해요. 지금 시작할 행동을 따로 부탁해 주세요.');
        return result(s, false, '행동을 할 주민에게 부탁해 주세요. 발판 준비, 문을 잡아 유지하기, 건너기의 조건을 살펴보세요.');
      },
      solutions: [{ listener: 'suri', spec: ['수리', ['서다', '발판']] }, { listener: 'moru', spec: ['모루', ['잡다', '문']] }, { listener: 'suri', spec: ['수리', '건너다'] }]
    }
  ];
  globalThis.SCENARIOS = [...(globalThis.SCENARIOS || []), ...items];
})();
