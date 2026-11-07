'use strict';
const button = document.querySelector('#sound-toggle');
const label = button.querySelector('.sound-label');
const status = document.querySelector('#sound-status');
const art = document.querySelector('.score-art');
let context = null, timer = null, playing = false;
function stop() {
  clearTimeout(timer);
  if (context) { context.close().catch(() => {}); context = null; }
  playing = false;
  button.setAttribute('aria-pressed', 'false');
  button.querySelector('.play-icon').textContent = '▶';
  label.textContent = '작은 모티프 들어보기';
  art.classList.remove('playing');
  status.textContent = '개념을 위한 합성 사운드 · AI 작곡 결과가 아닙니다';
}
button.addEventListener('click', async () => {
  if (playing) { stop(); return; }
  const AudioEngine = window.AudioContext || window.webkitAudioContext;
  if (!AudioEngine) { status.textContent = '이 브라우저에서는 사운드 재생을 지원하지 않습니다.'; return; }
  try {
    const engine = new AudioEngine(); context = engine;
    playing = true; button.setAttribute('aria-pressed', 'true');
    await engine.resume();
    if (context !== engine) return;
    const master = engine.createGain(); master.gain.value = 0.22; master.connect(engine.destination);
    function note(midi, when, duration, volume) {
      const osc = engine.createOscillator(), gain = engine.createGain();
      osc.type = 'triangle'; osc.frequency.value = 440 * Math.pow(2, (midi - 69) / 12);
      const t = engine.currentTime + when;
      gain.gain.setValueAtTime(0, t); gain.gain.linearRampToValueAtTime(volume, t + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.001, t + duration);
      osc.connect(gain); gain.connect(master); osc.start(t); osc.stop(t + duration + 0.03);
    }
    // Original illustrative motif. No model, sample download, or personal music data.
    [[64,0,1.8],[67,2,0.9],[71,3,1.8],[69,5,0.9],[72,6,1.85]].forEach(n => note(...n,0.5));
    [48,55,59].forEach(n => note(n,0,3.7,0.18));
    [53,57,60].forEach(n => note(n,4,3.8,0.16));
    button.querySelector('.play-icon').textContent = '■'; label.textContent = '재생 멈추기';
    status.textContent = '재생 중 · 브라우저에서 합성한 8초 모티프'; art.classList.add('playing');
    timer = setTimeout(stop, 8050);
  } catch (_) { stop(); status.textContent = '사운드를 시작하지 못했습니다. 다시 시도해 주세요.'; }
});
document.addEventListener('visibilitychange', () => { if (document.hidden && playing) stop(); });

// Progressive enhancement: commands remain selectable without clipboard support.
if (navigator.clipboard && window.isSecureContext) {
  document.querySelectorAll('.copy-code').forEach(copyButton => {
    copyButton.hidden = false;
    copyButton.addEventListener('click', async () => {
      const code = document.getElementById(copyButton.dataset.copy);
      const feedback = document.getElementById('copy-status');
      try {
        await navigator.clipboard.writeText(code.textContent);
        copyButton.textContent = '복사됨 ✓';
        feedback.textContent = copyButton.getAttribute('aria-label') + ' 완료';
      } catch (_) {
        feedback.textContent = '복사하지 못했습니다. 코드 영역의 명령을 직접 선택해 복사해 주세요.';
        copyButton.textContent = '직접 선택해 주세요';
      }
      setTimeout(() => { copyButton.textContent = '복사'; }, 2500);
    });
  });
}
