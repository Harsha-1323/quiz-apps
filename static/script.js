let currentIndex = 0;
let answers = {};
let timer = null;
let timeLeft = 0;

function renderQuestion() {
  const area = document.getElementById('question-area');
  if (!QUESTIONS || QUESTIONS.length === 0) {
    area.innerHTML = "<p>No questions available.</p>";
    return;
  }
  if (currentIndex >= QUESTIONS.length) {
    area.innerHTML = "<p class='text-center'>All done — ready to submit.</p>";
    document.getElementById('submitBtn').classList.remove('hidden');
    document.getElementById('nextBtn').classList.add('hidden');
    document.getElementById('prevBtn').classList.add('hidden');
    document.getElementById('timer').textContent = 0;
    return;
  }

  const q = QUESTIONS[currentIndex];
  let html = `<div>
    <p class="font-semibold text-lg">${currentIndex+1}. ${q.text}</p>
    <div class="mt-3 space-y-2">
      <label><input type="radio" name="opt" value="A" ${answers[q.id]=='A'?'checked':''}> A. ${q.option_a}</label><br>
      <label><input type="radio" name="opt" value="B" ${answers[q.id]=='B'?'checked':''}> B. ${q.option_b}</label><br>
      ${q.option_c?'<label><input type="radio" name="opt" value="C" '+(answers[q.id]=='C'?'checked':'')+'> C. '+q.option_c+'</label><br>':''}
      ${q.option_d?'<label><input type="radio" name="opt" value="D" '+(answers[q.id]=='D'?'checked':'')+'> D. '+q.option_d+'</label><br>':''}
    </div>
  </div>`;
  area.innerHTML = html;
  document.getElementById('qindex').textContent = currentIndex+1;
  document.getElementById('qtotal').textContent = QUESTIONS.length;

  const radios = document.getElementsByName('opt');
  radios.forEach(r => r.addEventListener('change', function() {
    answers[q.id] = this.value;
  }));

  startTimer();
}

function startTimer() {
  clearInterval(timer);
  timeLeft = TIME_PER_Q || 20;
  document.getElementById('timer').textContent = timeLeft;
  timer = setInterval(() => {
    timeLeft -= 1;
    document.getElementById('timer').textContent = timeLeft;
    if (timeLeft <= 0) {
      clearInterval(timer);
      goNext();
    }
  }, 1000);
}

function goNext() {
  saveCurrentSelection();
  currentIndex++;
  renderQuestion();
}

function goPrev() {
  if (currentIndex > 0) currentIndex--;
  renderQuestion();
}

function saveCurrentSelection() {
  const radios = document.getElementsByName('opt');
  if (radios && radios.length>0) {
    radios.forEach(r => { if (r.checked) answers[QUESTIONS[currentIndex].id] = r.value; });
  }
}

function submitQuiz() {
  clearInterval(timer);
  saveCurrentSelection();

  fetch(window.location.pathname, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(answers)
  }).then(r => r.json()).then(data => {
    if (data.status === 'ok') {
      window.location.href = '/result';
    } else {
      alert('Error submitting quiz');
    }
  }).catch(e => {
    alert('Network error');
  });
}

document.addEventListener('DOMContentLoaded', function() {
  if (typeof QUESTIONS !== 'undefined' && QUESTIONS.length > 0) {
    renderQuestion();
  }
  const nextBtn = document.getElementById('nextBtn');
  const prevBtn = document.getElementById('prevBtn');
  const submitBtn = document.getElementById('submitBtn');

  if (nextBtn) nextBtn.addEventListener('click', goNext);
  if (prevBtn) prevBtn.addEventListener('click', goPrev);
  if (submitBtn) submitBtn.addEventListener('click', submitQuiz);
});

