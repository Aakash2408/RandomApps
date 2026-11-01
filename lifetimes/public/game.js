// Lifetimes: a text life simulator. Plain JS, no build step, saves to localStorage.
'use strict';

// ---------- helpers ----------
const $ = (s) => document.querySelector(s);
const rnd = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a;
const chance = (p) => Math.random() < p;
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const clamp = (v) => Math.max(0, Math.min(100, Math.round(v)));
const money = (n) => (n < 0 ? '-' : '') + '$' + Math.abs(Math.round(n)).toLocaleString('en-US');
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// ---------- world data ----------
const COUNTRIES = {
  'United States': { m: ['James', 'Liam', 'Noah', 'Ethan', 'Mason', 'Lucas', 'Caleb', 'Owen'], f: ['Emma', 'Olivia', 'Ava', 'Mia', 'Harper', 'Ella', 'Chloe', 'Grace'], last: ['Smith', 'Johnson', 'Brown', 'Miller', 'Davis', 'Garcia', 'Wilson', 'Clark'] },
  'India': { m: ['Aarav', 'Vihaan', 'Arjun', 'Kabir', 'Rohan', 'Ishaan', 'Dev', 'Aditya'], f: ['Ananya', 'Diya', 'Saanvi', 'Isha', 'Meera', 'Kavya', 'Riya', 'Priya'], last: ['Sharma', 'Patel', 'Iyer', 'Singh', 'Reddy', 'Nair', 'Gupta', 'Das'] },
  'United Kingdom': { m: ['Oliver', 'George', 'Harry', 'Jack', 'Alfie', 'Leo', 'Archie', 'Freddie'], f: ['Amelia', 'Isla', 'Lily', 'Freya', 'Poppy', 'Evie', 'Rosie', 'Ivy'], last: ['Taylor', 'Jones', 'Evans', 'Wright', 'Walker', 'Hughes', 'Hall', 'Wood'] },
  'Brazil': { m: ['Miguel', 'Arthur', 'Heitor', 'Davi', 'Gabriel', 'Pedro', 'Rafael', 'Bernardo'], f: ['Helena', 'Alice', 'Laura', 'Valentina', 'Sofia', 'Julia', 'Beatriz', 'Livia'], last: ['Silva', 'Santos', 'Oliveira', 'Souza', 'Lima', 'Costa', 'Pereira', 'Alves'] },
  'Nigeria': { m: ['Chinedu', 'Tunde', 'Emeka', 'Femi', 'Ifeanyi', 'Kunle', 'Obinna', 'Segun'], f: ['Amara', 'Ngozi', 'Funmi', 'Chioma', 'Zainab', 'Ada', 'Yetunde', 'Temi'], last: ['Okafor', 'Adeyemi', 'Okonkwo', 'Bello', 'Eze', 'Balogun', 'Nwosu', 'Ogunleye'] },
  'Japan': { m: ['Haruto', 'Sota', 'Yuto', 'Ren', 'Riku', 'Kaito', 'Hinata', 'Sora'], f: ['Yui', 'Hina', 'Sakura', 'Aoi', 'Mei', 'Rin', 'Yuna', 'Koharu'], last: ['Sato', 'Suzuki', 'Takahashi', 'Tanaka', 'Ito', 'Watanabe', 'Kato', 'Kobayashi'] },
  'Mexico': { m: ['Santiago', 'Mateo', 'Sebastian', 'Leonardo', 'Diego', 'Emiliano', 'Daniel', 'Iker'], f: ['Sofia', 'Regina', 'Valeria', 'Camila', 'Ximena', 'Renata', 'Mariana', 'Fernanda'], last: ['Hernandez', 'Lopez', 'Martinez', 'Gonzalez', 'Perez', 'Ramirez', 'Flores', 'Torres'] },
  'United Arab Emirates': { m: ['Omar', 'Khalid', 'Saeed', 'Rashid', 'Hamdan', 'Zayed', 'Faisal', 'Majid'], f: ['Mariam', 'Fatima', 'Noura', 'Aisha', 'Shamma', 'Hessa', 'Latifa', 'Maitha'], last: ['Al Mansoori', 'Al Hashimi', 'Al Nuaimi', 'Al Ketbi', 'Al Suwaidi', 'Al Falasi', 'Al Mazrouei', 'Al Shamsi'] },
};

const EDU_LABEL = { hs: 'High school diploma', trade: 'Trade certificate', degree: "Bachelor's degree", medical: 'Medical degree', law: 'Law degree' };

const CAREERS = [
  { id: 'food', name: 'Fast food', edu: null, sm: 0, ladder: [['Crew Member', 18000], ['Shift Lead', 24000], ['Restaurant Manager', 42000]] },
  { id: 'retail', name: 'Retail', edu: null, sm: 10, ladder: [['Sales Associate', 22000], ['Supervisor', 30000], ['Store Manager', 55000]] },
  { id: 'warehouse', name: 'Logistics', edu: null, sm: 0, ladder: [['Warehouse Worker', 28000], ['Forklift Operator', 36000], ['Logistics Manager', 68000]] },
  { id: 'music', name: 'Music', edu: null, sm: 0, looks: 45, ladder: [['Street Performer', 8000], ['Session Musician', 35000], ['Touring Artist', 140000], ['Superstar', 2500000]] },
  { id: 'trade', name: 'Electrical', edu: 'trade', sm: 20, ladder: [['Apprentice Electrician', 32000], ['Electrician', 58000], ['Master Electrician', 90000]] },
  { id: 'teach', name: 'Education', edu: 'degree', sm: 40, ladder: [['Teacher', 46000], ['Senior Teacher', 60000], ['Principal', 95000]] },
  { id: 'nurse', name: 'Nursing', edu: 'degree', sm: 45, ladder: [['Nurse', 62000], ['Charge Nurse', 78000], ['Head of Nursing', 105000]] },
  { id: 'tech', name: 'Software', edu: 'degree', sm: 60, ladder: [['Junior Developer', 72000], ['Software Engineer', 115000], ['Engineering Manager', 170000], ['CTO', 280000]] },
  { id: 'biz', name: 'Business', edu: 'degree', sm: 50, ladder: [['Analyst', 60000], ['Manager', 95000], ['Director', 160000], ['CEO', 480000]] },
  { id: 'doctor', name: 'Medicine', edu: 'medical', sm: 75, ladder: [['Resident', 62000], ['Doctor', 215000], ['Surgeon', 390000]] },
  { id: 'law', name: 'Law', edu: 'law', sm: 70, ladder: [['Associate', 98000], ['Senior Associate', 155000], ['Partner', 420000]] },
];
CAREERS.push(...CONTENT.careers);
const careerById = (id) => CAREERS.find((c) => c.id === id);

const ACHIEVEMENTS = {
  graduate: 'Graduated university', married: 'Tied the knot', parent: 'Became a parent', millionaire: 'Millionaire',
  centenarian: 'Lived to 100', ceo: 'Became a CEO', surgeon: 'Became a surgeon', superstar: 'Became a superstar',
  homeowner: 'Bought a home', lottery: 'Won the lottery', legacy: 'Continued as your child', fit: 'Peak fitness (health 100)',
};
Object.assign(ACHIEVEMENTS, CONTENT.achievements);

// ---------- purchases (in-app, verified server-side) ----------
const PACKS = {
  plus: { name: 'Lifetimes Plus', blurb: '5 actions a year instead of 3, and choose your name, country and gender for every new life.' },
  editor: { name: 'Destiny Editor', blurb: 'Set your happiness, health, smarts and looks any time.' },
  rewind: { name: 'Second Chance', blurb: 'When you die, rewind up to 5 years and try again. Pay once, rewind forever. Never per use.' },
  careers: { name: 'Dream Jobs', blurb: '8 extra careers: astronaut, pro athlete, pilot, streamer, politician, detective, fashion designer and game developer.' },
  drama: { name: 'Life Drama', blurb: '15 big, wild life events: reality TV, haunted mansions, bank robberies, secret siblings, island challenges and more.' },
};
const owned = { plus: false, editor: false, rewind: false, careers: false, drama: false };
const MODES = {
  classic: { icon: '🌱', name: 'Classic', desc: 'Live however you like.' },
  hardcore: { icon: '💀', name: 'Hardcore', desc: 'One fewer action a year, harsher health, a humbler start. No rewinds, no Destiny Editor.' },
  challenge: { icon: '🎯', name: 'Challenge', desc: 'Pick a goal and try to hit it in one life.' },
};
const isHardcore = () => P && P.mode === 'hardcore';
const challengeOf = () => (P && P.mode === 'challenge' ? CONTENT.challenges.find((c) => c.id === P.challenge) : null);

// ---------- state ----------
let P = null;          // the current person
let history = [];      // snapshots for Second Chance
let pendingChoice = null;

function newPerson(opts = {}) {
  const country = opts.country || pick(Object.keys(COUNTRIES));
  const gender = opts.gender || pick(['m', 'f']);
  const c = COUNTRIES[country];
  const last = opts.last || pick(c.last);
  const first = opts.first || pick(c[gender]);
  const parentsLast = last;
  const wealth = opts.wealth ?? pick([0, 0, 1, 1, 1, 2, 2, 3]); // 0 poor .. 3 rich
  const p = {
    id: Math.random().toString(36).slice(2), first, last, gender, country, age: 0, alive: true,
    s: { happy: opts.happy ?? rnd(50, 95), health: opts.health ?? rnd(70, 100), smarts: opts.smarts ?? rnd(10, 90), looks: opts.looks ?? rnd(10, 95) },
    cash: opts.cash ?? 0, debt: 0, wealth, edu: {}, school: null, job: null, retired: false, pension: 0,
    record: 0, ill: null, assets: [], people: [], log: [], actionsUsed: 0, generation: opts.generation || 1,
    perf: 0, causeOfDeath: '', achievements: [],
  };
  const parentAge = () => rnd(22, 40);
  p.people.push(person(pick(c.f), parentsLast, 'f', 'Mother', parentAge(), rnd(60, 95)));
  p.people.push(person(pick(c.m), parentsLast, 'm', 'Father', parentAge(), rnd(50, 95)));
  for (let i = 0; i < pick([0, 0, 1, 1, 2]); i++) {
    const g = pick(['m', 'f']);
    const taken = p.people.map((x) => x.first).concat(first);
    const name = pick(c[g].filter((n) => !taken.includes(n)));
    p.people.push(person(name, parentsLast, g, g === 'm' ? 'Brother' : 'Sister', rnd(1, 8), rnd(40, 90)));
  }
  return p;
}

function person(first, last, gender, rel, age, bond) {
  return { id: Math.random().toString(36).slice(2), first, last, gender, rel, age, bond, alive: true, years: 0 };
}

const fullName = (x) => `${x.first} ${x.last}`;
const partner = () => P.people.find((x) => x.alive && (x.rel === 'Partner' || x.rel === 'Spouse'));
const kids = () => P.people.filter((x) => x.rel === 'Son' || x.rel === 'Daughter');
const livingKids = () => kids().filter((x) => x.alive);
const hasHome = () => P.assets.some((a) => a.kind === 'home');
const netWorth = () => P.cash - P.debt + P.assets.reduce((t, a) => t + a.value, 0);
const maxActions = () => (owned.plus ? 5 : 3) - (isHardcore() ? 1 : 0);
const salary = () => (P.job ? careerById(P.job.career).ladder[P.job.level][1] : 0);
const jobTitle = () => (P.job ? careerById(P.job.career).ladder[P.job.level][0] : '');

function log(text, kind = '') { P.log.push({ age: P.age, text, kind }); }
function bump(stat, d) { P.s[stat] = clamp(P.s[stat] + d); }
function unlock(key) {
  if (P.achievements.includes(key)) return;
  P.achievements.push(key);
  log(`Achievement unlocked: ${ACHIEVEMENTS[key]}`, 'good');
  const all = JSON.parse(localStorage.getItem('lt_ach') || '[]');
  if (!all.includes(key)) { all.push(key); localStorage.setItem('lt_ach', JSON.stringify(all)); }
}

// ---------- the year loop ----------
function ageUp() {
  if (!P || !P.alive || pendingChoice) return;
  history.push(JSON.stringify(P));
  if (history.length > 6) history.shift();
  P.age += 1;
  P.actionsUsed = 0;
  log(`Age ${P.age}`, 'year');

  yearlyDrift();
  schooling();
  finances();
  peopleYear();
  if (deathCheck()) return finish();
  randomEvent();
  milestones();
  if (P.log[P.log.length - 1].kind === 'year' && !pendingChoice) quietYear();
  save();
  render();
}

function quietYear() {
  const study = { degree: 'university', trade: 'trade school', medical: 'medical school', law: 'law school' }[P.school];
  if (study) return log(pick([`Another year of ${study}.`, `You pulled some all-nighters at ${study}.`, `You made a few good friends at ${study}.`]));
  if (!chance(0.55)) return;
  const lines = P.age < 5 ? ['You spent the year napping and exploring.', 'You learned some new words.']
    : P.age < 13 ? ['You played outside a lot this year.', 'You got really into a cartoon.', 'You had a fun summer break.']
    : P.age < 18 ? ['You spent too much time on your phone.', 'You got your first crush.', 'You argued with your parents about curfew.']
    : P.job ? (careerById(P.job.career).lines || []).concat([`Work as a ${jobTitle()} kept you busy.`, 'You picked up a new hobby.'])
    : P.retired ? ['You enjoyed a slow, peaceful year.', 'You spent time in the garden.'] : ['You spent the year figuring out what to do next.', 'Money was tight this year.'];
  log(pick(lines));
}

function yearlyDrift() {
  const s = P.s;
  if (P.age > 50) bump('health', -rnd(0, Math.ceil((P.age - 45) / 8)));
  if (P.age > 35) bump('looks', -rnd(0, 1));
  if (P.age < 18) bump('smarts', rnd(0, 2));
  if (P.debt > P.cash + 20000 && P.age >= 18) { bump('happy', -rnd(1, 4)); }
  if (P.ill) {
    bump('health', -P.ill.severity * (isHardcore() ? 1.5 : 1));
    if (chance(0.25)) { log(`Your ${P.ill.name} cleared up on its own.`, 'good'); P.ill = null; }
  }
  if (s.happy < 20 && chance(0.2)) log('You have been feeling really low lately.', 'bad');
  if (s.health >= 100) unlock('fit');
}

function schooling() {
  if (P.age === 5) { P.school = 'school'; log('You started school.'); }
  if (P.school === 'school' && P.age >= 18) {
    P.school = null; P.edu.hs = true; log('You graduated from high school!', 'good');
    choose({
      text: 'You finished high school. What next?',
      options: [
        { label: 'Go to university (4 years, student loans)', run: () => { P.school = 'degree'; P.schoolLeft = 4; return 'You enrolled at university.'; } },
        { label: 'Go to trade school (2 years)', run: () => { P.school = 'trade'; P.schoolLeft = 2; return 'You enrolled in trade school.'; } },
        { label: 'Start working', run: () => 'You decided to skip further study and work.' },
        { label: 'Take a gap year', run: () => { bump('happy', 8); return 'You took a gap year to travel and think.'; } },
      ],
    });
    return;
  }
  if (['degree', 'trade', 'medical', 'law'].includes(P.school) && P.age > 18) {
    const cost = { degree: 22000, trade: 9000, medical: 45000, law: 40000 }[P.school];
    P.debt += cost;
    bump('smarts', rnd(2, 5));
    P.schoolLeft -= 1;
    if (P.schoolLeft <= 0) {
      const done = P.school; P.edu[done] = true; P.school = null;
      log(`You earned your ${EDU_LABEL[done].toLowerCase()}!`, 'good');
      if (done === 'degree') {
        unlock('graduate');
        if (P.s.smarts >= 60) choose({
          text: 'With your degree in hand, want to keep studying?',
          options: [
            { label: 'Apply to medical school (4 years)', run: () => (P.s.smarts >= 70 && chance(0.4 + (P.s.smarts - 70) / 60) ? (P.school = 'medical', P.schoolLeft = 4, 'You got into medical school!') : 'Medical school rejected you.') },
            { label: 'Apply to law school (3 years)', run: () => (P.s.smarts >= 65 && chance(0.45 + (P.s.smarts - 65) / 60) ? (P.school = 'law', P.schoolLeft = 3, 'You got into law school!') : 'Law school rejected you.') },
            { label: "No, I'm done studying", run: () => 'You were ready to start your career.' },
          ],
        });
      }
    }
  }
}

function finances() {
  if (P.job) {
    const net = salary() * 0.72;
    P.cash += net;
    P.perf = Math.max(-3, Math.min(5, P.perf + (P.s.happy + P.s.smarts - 100) / 100 + (Math.random() - 0.5)));
    const c = careerById(P.job.career);
    if (P.job.level < c.ladder.length - 1 && P.job.years >= 1 && chance(0.1 + Math.max(0, P.perf) * 0.08)) {
      P.job.level += 1; P.perf = 0;
      log(`You were promoted to ${jobTitle()}! New salary: ${money(salary())}.`, 'good');
      bump('happy', 6);
      if (jobTitle() === 'CEO') unlock('ceo');
      if (jobTitle() === 'Surgeon') unlock('surgeon');
      if (jobTitle() === 'Superstar') unlock('superstar');
      if (c.top && P.job.level === c.ladder.length - 1) unlock(c.top);
    } else if (P.perf < -2.5 && chance(0.35)) {
      log(`You were fired from your job as ${jobTitle()}.`, 'bad');
      P.job = null; P.perf = 0; bump('happy', -10);
    }
    if (P.job) P.job.years += 1;
    if (P.job && c.maxAge && P.age > c.maxAge) { log(`At ${P.age}, your body says it's time. You retired from ${c.name.toLowerCase()}.`, 'hint'); P.pension = Math.round(salary() * 0.15); P.retired = true; P.job = null; }
  }
  if (P.retired) P.cash += P.pension;
  if (P.age >= 18 && !P.school && !(P.age < 22 && !P.job && parentsAlive())) {
    const lifestyle = 0.35 * (salary() * 0.72 + (P.retired ? P.pension : 0));
    const income = P.job || P.retired;
    const living = (hasHome() ? 9000 : income ? 17000 : 8000) + lifestyle + livingKids().filter((k) => k.age < 18).length * 7000;
    P.cash -= living;
  }
  if (P.cash < 0) { P.debt += -P.cash; P.cash = 0; }
  if (P.debt > 0 && P.cash > 0) { const pay = Math.min(P.cash * 0.5, P.debt); P.cash -= pay; P.debt -= pay; }
  P.debt = Math.round(P.debt * 1.04);
  // Debts this deep with nothing to sell: bankruptcy wipes them, at a cost.
  const assetValue = P.assets.reduce((t, a) => t + a.value, 0);
  if (P.debt > 150000 && P.cash < 1000 && P.debt > assetValue * 1.2 && !P.school) {
    if (P.assets.length) log(`The bank repossessed everything you owned (${money(assetValue)}).`, 'bad');
    log(`You declared bankruptcy. ${money(Math.max(0, P.debt - assetValue))} of debt was wiped out, but it hurt.`, 'bad');
    P.assets = []; P.debt = 0; bump('happy', -15);
  }
  for (const a of P.assets) a.value = Math.round(a.value * (a.kind === 'home' ? 1.03 : 0.85));
  P.assets = P.assets.filter((a) => a.value > 300);
  if (netWorth() >= 1e6) unlock('millionaire');
}

const parentsAlive = () => P.people.some((x) => (x.rel === 'Mother' || x.rel === 'Father') && x.alive);

function peopleYear() {
  for (const x of P.people) {
    if (!x.alive) continue;
    x.age += 1;
    if (x.rel === 'Partner' || x.rel === 'Spouse') x.years += 1;
    if (!(x.rel === 'Son' || x.rel === 'Daughter') || x.age > 18) x.bond = clamp(x.bond - rnd(0, 3));
    const p = 0.0003 * Math.exp(0.085 * (x.age - 20));
    if (x.age > 30 && chance(p)) {
      x.alive = false;
      log(`Your ${x.rel.toLowerCase()} ${fullName(x)} died at age ${x.age}.`, 'bad');
      bump('happy', -(x.bond > 60 ? 15 : 6));
      if ((x.rel === 'Mother' || x.rel === 'Father') && chance(0.6)) {
        const inherit = rnd(1, 4) * 5000 * (P.wealth + 1) * (P.wealth === 3 ? 10 : 1);
        P.cash += inherit;
        log(`You inherited ${money(inherit)}.`, 'good');
      }
      if (x.rel === 'Spouse') x.rel = 'Late spouse';
    }
    if ((x.rel === 'Partner' || x.rel === 'Spouse') && x.alive && x.bond < 15 && chance(0.4)) {
      log(`${x.first} left you.`, 'bad');
      x.rel = x.rel === 'Spouse' ? 'Ex-spouse' : 'Ex'; bump('happy', -12);
      if (x.rel === 'Ex-spouse' && P.cash > 0) { const half = Math.round(P.cash / 2); P.cash -= half; log(`The divorce cost you ${money(half)}.`, 'bad'); }
    }
  }
}

function deathCheck() {
  if (P.s.health <= 0) { P.causeOfDeath = P.ill ? `complications from ${P.ill.name}` : 'poor health'; return true; }
  let p = P.age < 2 ? 0.002 : 0.0003 * Math.exp(0.085 * (P.age - 20));
  if (P.s.health < 30) p *= 1 + (30 - P.s.health) / 8;
  if (P.age > 20 && P.s.happy < 10) p *= 1.5;
  if (isHardcore()) p *= 1.6;
  if (chance(p)) {
    P.causeOfDeath = P.age > 75 ? pick(['old age', 'heart failure', 'a stroke', 'old age']) : pick(['a car accident', 'a heart attack', 'a sudden illness', 'an accident at home']);
    return true;
  }
  return false;
}

function milestones() {
  if (P.age === 100) unlock('centenarian');
  if (P.age === 80 && isHardcore()) unlock('hardcore80');
  if (P.age === 16) log('You can now look for part-time work and go on dates.', 'hint');
  if (P.age === 65 && P.job) log('You are old enough to retire. Find "Retire" under Career.', 'hint');
}

// ---------- random events ----------
const PASSIVE = [
  { min: 1, max: 4, p: 0.25, run: () => { bump('happy', 3); return pick(['You said your first word: "' + pick(['cookie', 'no', 'dog', 'mama', 'ball']) + '".', 'You learned to ride a tricycle.', 'You built an impressive block tower.']); } },
  { min: 2, max: 10, p: 0.12, run: () => { bump('health', -rnd(2, 6)); return pick(['You caught chickenpox.', 'You fell off the monkey bars and sprained your wrist.', 'You had a bad ear infection.']); } },
  { min: 6, max: 17, p: 0.18, run: () => { const g = P.s.smarts > 60; bump('happy', g ? 4 : -3); return g ? 'You got top marks on your report card.' : 'Your report card was disappointing.'; } },
  { min: 13, max: 17, p: 0.12, run: () => { bump('looks', -rnd(1, 4)); return 'You went through an awkward growth spurt.'; } },
  { min: 18, max: 90, p: 0.08, when: () => P.assets.some((a) => a.kind === 'car'), run: () => { const f = rnd(200, 2000); P.cash -= f; bump('happy', -2); return `Your car broke down. Repairs cost ${money(f)}.`; } },
  { min: 18, max: 90, p: 0.05, run: () => { const f = rnd(100, 1500); P.cash += f; bump('happy', 3); return `You found ${money(f)} you forgot about in an old account.`; } },
  { min: 25, max: 90, p: 0.07, run: () => { const names = ['the flu', 'pneumonia', 'back pain', 'high blood pressure', 'a stomach ulcer']; P.ill = { name: pick(names), severity: rnd(3, 8) }; return `You were diagnosed with ${P.ill.name}. A doctor could help.`; } },
  { min: 50, max: 100, p: 0.05, run: () => { P.ill = { name: pick(['arthritis', 'diabetes', 'heart disease']), severity: rnd(4, 10) }; return `You were diagnosed with ${P.ill.name}.`; } },
  { min: 20, max: 80, p: 0.05, run: () => { bump('happy', 6); return pick(['You adopted a stray cat. It ignores you, lovingly.', 'You picked up gardening and grew a giant pumpkin.', 'You ran your first 10K.']); } },
];

const CHOICES = [
  { min: 4, max: 10, p: 0.15, text: () => 'A kid at school pushed you on the playground.', options: [
    { label: 'Push them back', run: () => (chance(0.5) ? (bump('happy', 3), 'You pushed back. They never bothered you again.') : (bump('happy', -4), 'You both got sent to the principal.')) },
    { label: 'Tell a teacher', run: () => (bump('happy', 1), 'The teacher sorted it out.') },
    { label: 'Ignore it', run: () => (bump('happy', -2), 'You walked away, upset.') },
  ] },
  { min: 8, max: 15, p: 0.12, text: () => 'Your parents offer to pay for lessons. Pick one.', options: [
    { label: 'Piano', run: () => (bump('smarts', 4), 'You started piano lessons.') },
    { label: 'Football', run: () => (bump('health', 4), bump('looks', 1), 'You joined a football team.') },
    { label: 'Coding club', run: () => (bump('smarts', 5), 'You started coding club and built a tiny game.') },
    { label: 'No thanks', run: () => 'You preferred your free time.' },
  ] },
  { min: 14, max: 17, p: 0.15, text: () => 'Friends invite you to a party on a school night.', options: [
    { label: 'Go', run: () => (bump('happy', 6), chance(0.3) ? (bump('smarts', -3), 'You had fun but bombed a test the next day.') : 'Best night of the year.') },
    { label: 'Stay home and study', run: () => (bump('smarts', 3), bump('happy', -2), 'You aced your test, but missed out.') },
  ] },
  { min: 15, max: 17, p: 0.12, text: () => 'Someone offers you a cigarette.', options: [
    { label: 'Try it', run: () => (bump('health', -4), 'You coughed for a minute straight. Not cool.') },
    { label: 'Say no', run: () => (bump('health', 1), 'You said no.') },
  ] },
  { min: 18, max: 60, p: 0.06, text: () => 'A friend asks to borrow $2,000.', when: () => P.cash >= 2000, options: [
    { label: 'Lend it', run: () => { P.cash -= 2000; if (chance(0.55)) { P.cash += 2000; return 'They paid you back a few months later.'; } bump('happy', -4); return 'You never saw that money again.'; } },
    { label: 'Say no', run: () => (bump('happy', -1), 'They understood. Mostly.') },
  ] },
  { min: 22, max: 60, p: 0.07, text: () => 'A coworker pitches you a startup idea and asks you to invest $10,000.', when: () => P.cash >= 10000, options: [
    { label: 'Invest', run: () => { P.cash -= 10000; const r = Math.random(); if (r < 0.08) { P.cash += 250000; bump('happy', 15); return 'The startup was acquired! Your stake paid out $250,000.'; } if (r < 0.35) { P.cash += 18000; return 'The startup did okay. You got $18,000 back.'; } return 'The startup folded. Your money is gone.'; } },
    { label: 'Pass', run: () => 'You kept your savings.' },
  ] },
  { min: 25, max: 70, p: 0.05, text: () => 'You are offered a job in another city with 20% higher pay.', when: () => !!P.job, options: [
    { label: 'Take it', run: () => { const extra = Math.round(salary() * 0.2); P.cash += extra; bump('happy', -3); return `You moved for the job and banked an extra ${money(extra)} this year, but you miss home.`; } },
    { label: 'Stay', run: () => (bump('happy', 2), 'You stayed close to the people you love.') },
  ] },
  { min: 18, max: 80, p: 0.04, text: () => 'You find a wallet with $300 and an ID inside.', options: [
    { label: 'Return it', run: () => (bump('happy', 4), 'You returned it. The owner hugged you.') },
    { label: 'Keep the cash', run: () => { P.cash += 300; bump('happy', -2); return 'You kept the cash. It felt a bit wrong.'; } },
  ] },
  { min: 60, max: 95, p: 0.06, text: () => 'Your grandkids want to visit for the summer.', when: () => livingKids().some((k) => k.age >= 22), options: [
    { label: 'Of course', run: () => (bump('happy', 8), 'It was a loud, happy summer.') },
    { label: 'Maybe next year', run: () => (bump('happy', -2), 'The house was quiet.') },
  ] },
];
PASSIVE.push(...CONTENT.passive);
CHOICES.push(...CONTENT.choices);

const shuffled = (a) => { const b = a.slice(); for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; };
const eventOk = (e) => P.age >= e.min && P.age <= e.max && (!e.pack || owned[e.pack]) && (!e.when || e.when());
function randomEvent() {
  if (pendingChoice) return;
  // Shuffled so events late in the list get the same shot as early ones.
  for (const e of shuffled(CHOICES.filter(eventOk))) if (chance(e.p)) { choose({ text: e.text(), options: e.options }); return; }
  for (const e of shuffled(PASSIVE.filter(eventOk))) if (chance(e.p)) { log(e.run(), e.pack ? 'drama' : ''); return; }
}

function choose(ev) { pendingChoice = ev; }

function resolveChoice(i) {
  const ev = pendingChoice; pendingChoice = null;
  const text = ev.options[i].run();
  if (text) log(text);
  if (P.cash < 0) { P.debt += -P.cash; P.cash = 0; }
  save(); render();
}

// ---------- actions (limited per year) ----------
function spend() {
  if (P.actionsUsed >= maxActions()) { toast(`You've used all ${maxActions()} actions this year. Age up to continue.`); return false; }
  P.actionsUsed += 1;
  return true;
}

function doAction(fn) { if (!spend()) return; const t = fn(); if (t) log(t); if (P.cash < 0) { P.debt += -P.cash; P.cash = 0; } closeSheet(); save(); render(); }

const ACTIVITIES = [
  { label: 'Study', min: 6, run: () => (bump('smarts', rnd(2, 6)), 'You hit the books.') },
  { label: 'Work out', min: 12, run: () => (bump('health', rnd(2, 6)), bump('looks', rnd(0, 3)), pick(['You went for a long run.', 'You lifted weights.', 'You tried a spin class.'])) },
  { label: 'Meditate', min: 10, run: () => (bump('happy', rnd(3, 7)), bump('health', 1), 'You meditated and felt calmer.') },
  { label: 'Party', min: 16, run: () => { bump('happy', rnd(5, 10)); bump('health', -rnd(1, 4)); if (!partner() && chance(0.15)) return meetSomeone('at a party'); return pick(['You danced all night.', 'You partied hard and woke up regretting it.']); } },
  { label: 'See a doctor ($300)', min: 0, run: () => { if (P.age >= 18) P.cash -= 300; if (P.ill) { const cured = chance(0.7); const n = P.ill.name; if (cured) P.ill = null; bump('health', rnd(4, 10)); return cured ? `The doctor treated your ${n}.` : `The doctor managed your ${n}, but it hasn't gone away.`; } bump('health', rnd(1, 4)); return 'You got a check-up. All good.'; } },
  { label: 'Go on vacation ($3,000)', min: 18, when: () => P.cash >= 3000, run: () => { P.cash -= 3000; bump('happy', rnd(8, 14)); return `You took a trip to ${pick(['Lisbon', 'Bali', 'Kyoto', 'Cape Town', 'Cancún', 'Istanbul'])}.`; } },
  { label: 'Find love', min: 16, when: () => !partner(), run: () => (chance(0.25 + P.s.looks / 200 + P.s.happy / 400) ? meetSomeone('on a dating app') : (bump('happy', -2), 'No luck in love this time.')) },
  { label: 'Buy a lottery ticket ($10)', min: 18, run: () => { P.cash -= 10; if (chance(1 / 200000)) { P.cash += 1e6; bump('happy', 25); unlock('lottery'); return 'YOU WON $1,000,000!'; } if (chance(1 / 40)) { P.cash += 100; return 'You won $100.'; } return 'Not a winning ticket.'; } },
  { label: 'Shoplift', min: 10, run: () => { if (chance(0.6)) { bump('happy', 2); return 'You slipped a candy bar into your pocket. Nobody noticed.'; } P.record += 1; bump('happy', -8); if (P.age < 18) return 'You got caught shoplifting. Your parents grounded you for a month.'; P.cash -= 800; return 'You were caught shoplifting and fined $800. It is on your record now.'; } },
];
ACTIVITIES.push(...CONTENT.activities);

function meetSomeone(where) {
  const c = COUNTRIES[P.country];
  const g = P.gender === 'm' ? (chance(0.92) ? 'f' : 'm') : (chance(0.92) ? 'm' : 'f');
  const age = P.age < 18 ? rnd(Math.max(16, P.age - 1), P.age + 1) : Math.max(18, P.age + rnd(-4, 4));
  const x = person(pick(c[g]), pick(c.last), g, 'Partner', age, rnd(50, 80));
  P.people.push(x);
  bump('happy', 8);
  return `You met ${fullName(x)} ${where}. You're dating now!`;
}

// ---------- career ----------
function eduOk(req) { return !req || !!P.edu[req]; }

function applyFor(c) {
  if (c.pack && !owned[c.pack]) return openStore(c.pack);
  if (!spend()) return;
  if (c.clean && P.record) { log(`${c.ladder[0][0]}: your criminal record ruled you out.`, 'bad'); closeSheet(); save(); render(); return; }
  if (c.maxAge && P.age > c.maxAge - 6) { log(`${c.ladder[0][0]}: they said you are too old to start.`, 'bad'); closeSheet(); save(); render(); return; }
  let odds = 0.55 + (P.s.smarts - c.sm) / 120 - P.record * 0.15;
  if (c.looks) odds = 0.35 + (P.s.looks - c.looks) / 100;
  if (c.hp) odds = Math.min(odds, 0.4 + (P.s.health - c.hp) / 60);
  if (chance(Math.max(0.05, Math.min(0.92, odds)))) {
    P.job = { career: c.id, level: 0, years: 0 }; P.perf = 0; P.retired = false;
    log(`You were hired as a ${c.ladder[0][0]} (${money(c.ladder[0][1])}/year).`, 'good'); bump('happy', 5);
  } else {
    log(`Your application for ${c.ladder[0][0]} was rejected.`, 'bad'); bump('happy', -2);
  }
  closeSheet(); save(); render();
}

function quitJob() { log(`You quit your job as ${jobTitle()}.`); P.job = null; closeSheet(); save(); render(); }
function workHarder() { doAction(() => { P.perf += rnd(1, 2); bump('happy', -1); return 'You put in extra hours at work.'; }); }
function retire() { P.pension = Math.round(salary() * 0.4); log(`You retired from your job as ${jobTitle()}. Pension: ${money(P.pension)}/year.`, 'good'); P.job = null; P.retired = true; bump('happy', 10); closeSheet(); save(); render(); }
function backToSchool() { P.school = 'degree'; P.schoolLeft = 4; if (P.job) { log(`You left your job to study.`); P.job = null; } log('You enrolled at university as a mature student.'); closeSheet(); save(); render(); }

// ---------- people ----------
function spendTime(x) { doAction(() => { x.bond = clamp(x.bond + rnd(5, 12)); bump('happy', 2); return `You spent quality time with your ${x.rel.toLowerCase()} ${x.first}.`; }); }
function propose(x) {
  doAction(() => {
    if (chance(0.3 + x.bond / 130 + x.years * 0.05)) { x.rel = 'Spouse'; x.bond = clamp(x.bond + 15); bump('happy', 15); unlock('married'); P.cash -= Math.min(P.cash, rnd(5000, 20000)); return `${x.first} said YES! You got married.`; }
    x.bond = clamp(x.bond - 15); bump('happy', -10); return `${x.first} said no. Ouch.`;
  });
}
function breakUp(x) { const div = x.rel === 'Spouse'; x.rel = div ? 'Ex-spouse' : 'Ex'; if (div && P.cash > 0) { const half = Math.round(P.cash / 2); P.cash -= half; log(`The divorce cost you ${money(half)}.`, 'bad'); } log(`You ${div ? 'divorced' : 'broke up with'} ${x.first}.`); bump('happy', -6); closeSheet(); save(); render(); }
function tryForBaby(x) {
  doAction(() => {
    const motherAge = P.gender === 'f' ? P.age : (x.gender === 'f' ? x.age : 30);
    if (motherAge > 45 || x.gender === P.gender) { return chance(0.5) ? adopt() : 'You decided to look into adoption next year.'; }
    if (!chance(motherAge < 35 ? 0.55 : 0.25)) return 'No baby yet. Keep trying.';
    return addChild(x);
  });
}
function adopt() { return addChild(null, true); }
function addChild(other, adopted = false) {
  const g = pick(['m', 'f']);
  const k = person(pick(COUNTRIES[P.country][g]), P.last, g, g === 'm' ? 'Son' : 'Daughter', 0, rnd(80, 100));
  k.s = { happy: rnd(60, 95), health: rnd(75, 100), smarts: clamp((P.s.smarts + (other ? rnd(20, 90) : rnd(10, 90))) / 2 + rnd(-10, 10)), looks: clamp((P.s.looks + rnd(10, 90)) / 2 + rnd(-10, 10)) };
  P.people.push(k); bump('happy', 12); unlock('parent');
  return adopted ? `You adopted a ${g === 'm' ? 'boy' : 'girl'}, ${k.first}.` : `Your ${g === 'm' ? 'son' : 'daughter'} ${k.first} was born!`;
}

// ---------- assets ----------
const SHOP = [
  { name: 'Used car', kind: 'car', price: 8000, happy: 5 },
  { name: 'New car', kind: 'car', price: 32000, happy: 9 },
  { name: 'Apartment', kind: 'home', price: 180000, happy: 10 },
  { name: 'Family house', kind: 'home', price: 420000, happy: 14 },
  { name: 'Beach villa', kind: 'home', price: 2200000, happy: 22 },
];
function buy(item) {
  const down = item.kind === 'home' ? item.price * 0.2 : item.price;
  if (P.cash < down) { toast(`You need ${money(down)} in cash${item.kind === 'home' ? ' for the deposit' : ''}.`); return; }
  if (item.kind === 'home' && item.price - down > salary() * 5) { toast(`The bank won't lend ${money(item.price - down)} on your income. Mortgages are capped at 5x your salary.`); return; }
  P.cash -= down; if (item.kind === 'home') P.debt += item.price - down;
  P.assets.push({ name: item.name, kind: item.kind, value: item.price });
  bump('happy', item.happy); if (item.kind === 'home') unlock('homeowner');
  log(`You bought a ${item.name.toLowerCase()} for ${money(item.price)}${item.kind === 'home' ? ` (${money(down)} deposit, the rest on a mortgage)` : ''}.`, 'good');
  closeSheet(); save(); render();
}
function sell(i) { const a = P.assets.splice(i, 1)[0]; P.cash += a.value; log(`You sold your ${a.name.toLowerCase()} for ${money(a.value)}.`); closeSheet(); save(); render(); }

// ---------- death + legacy ----------
function finish() {
  P.alive = false;
  pendingChoice = null;
  log(`You died at age ${P.age} from ${P.causeOfDeath}.`, 'bad');
  save(); render(); SFX.play('death'); openDeath();
}

function continueAs(k) {
  const share = Math.max(0, netWorth()) * 0.6 / Math.max(1, livingKids().length);
  const prev = P;
  const c = { first: k.first, last: k.last, gender: k.gender, country: prev.country, wealth: Math.min(3, prev.wealth + (share > 5e5 ? 1 : 0)), cash: Math.round(share), generation: prev.generation + 1, ...(k.s || {}) };
  P = newPerson(c);
  P.age = k.age;
  P.people = P.people.filter((x) => x.rel !== 'Mother' && x.rel !== 'Father');
  const parentRel = prev.gender === 'm' ? 'Father' : 'Mother';
  P.people.unshift(Object.assign(person(prev.first, prev.last, prev.gender, parentRel, prev.age, k.bond), { alive: false }));
  const other = prev.people.find((x) => x.alive && x.rel === 'Spouse');
  if (other) P.people.unshift(person(other.first, other.last, other.gender, other.gender === 'm' ? 'Father' : 'Mother', other.age, rnd(50, 90)));
  for (const sib of prev.people.filter((x) => (x.rel === 'Son' || x.rel === 'Daughter') && x.id !== k.id && x.alive)) P.people.push(person(sib.first, sib.last, sib.gender, sib.gender === 'm' ? 'Brother' : 'Sister', sib.age, rnd(40, 80)));
  if (k.age >= 18) P.edu.hs = true; else if (k.age >= 5) P.school = 'school';
  P.mode = prev.mode === 'hardcore' ? 'hardcore' : 'classic'; P.challenge = null;
  history = [];
  log(`Generation ${P.generation}: you are ${fullName(P)}, age ${P.age}. You inherited ${money(share)} from ${prev.first}.`, 'good');
  unlock('legacy');
  closeSheet(); save(); render();
}

function rewind() {
  if (!owned.rewind || !history.length || isHardcore()) return;
  const target = Math.max(0, history.length - 5);
  P = JSON.parse(history[target]);
  history = history.slice(0, target);
  log('Second Chance: you rewound time.', 'good');
  closeSheet(); save(); render();
}

// ---------- persistence ----------
function save() { if (P) checkChallenge(); try { localStorage.setItem('lt_save', JSON.stringify({ P, history })); } catch (e) { /* storage full: keep playing */ } }
function load() {
  try { const d = JSON.parse(localStorage.getItem('lt_save') || 'null'); if (d && d.P) { P = d.P; history = d.history || []; return true; } } catch (e) { /* corrupt save */ }
  return false;
}

// ---------- rendering ----------
const FLAGS = { 'United States': '🇺🇸', 'India': '🇮🇳', 'United Kingdom': '🇬🇧', 'Brazil': '🇧🇷', 'Nigeria': '🇳🇬', 'Japan': '🇯🇵', 'Mexico': '🇲🇽', 'United Arab Emirates': '🇦🇪' };
function avatar(x) {
  if (!x.alive) return '🪦';
  const f = x.gender === 'f';
  if (x.age < 3) return '👶';
  if (x.age < 13) return f ? '👧' : '👦';
  if (x.age < 60) return f ? '👩' : '👨';
  return f ? '👵' : '👴';
}

let lastStats = null, lastAge = null, lastId = null, lastLogLen = 0;
// One sound per render, picked from the most notable thing just logged.
function soundFor(entries, aged) {
  const t = entries.map((e) => e.text).join(' ');
  if (/Achievement unlocked|Challenge complete/.test(t)) return 'achievement';
  if (/married|said YES|You're dating|was born!|You adopted/.test(t)) return 'love';
  if (/promoted|You were hired|inherited|WON|bonus|reward/.test(t)) return 'money';
  if (entries.some((e) => e.kind === 'bad')) return 'bad';
  if (entries.some((e) => e.kind === 'good')) return 'good';
  return aged ? 'age' : '';
}
function render() {
  if (!P) return;
  $('#avatar').textContent = avatar(P);
  $('#who').textContent = fullName(P);
  $('#meta').textContent = `${FLAGS[P.country] || '🌍'} ${P.alive ? 'Age ' + P.age : 'Died at ' + P.age} · ${P.country}${P.generation > 1 ? ' · Gen ' + P.generation : ''}`;
  $('#cash').textContent = money(P.cash);
  $('#cash').classList.toggle('neg', P.cash < 0);
  $('#cash').title = `Net worth ${money(netWorth())}${P.debt ? ' · Debt ' + money(P.debt) : ''}`;
  // A new person (birth, heir) resets the comparison so their starting stats don't flash as changes.
  const samePerson = lastId === P.id;
  for (const k of ['happy', 'health', 'smarts', 'looks']) {
    const v = P.s[k];
    const bar = $(`#bar-${k}`); bar.style.width = v + '%'; bar.className = 'fill ' + (v < 25 ? 'lo' : v < 55 ? 'mid' : 'hi');
    $(`#val-${k}`).textContent = v + '%';
    $(`#stat-${k}`).setAttribute('aria-valuenow', v);
    const d = samePerson && lastStats ? v - lastStats[k] : 0;
    if (d) {
      const tile = $(`#stat-${k}`);
      tile.querySelector('.delta')?.remove();
      const el = document.createElement('span');
      el.className = 'delta ' + (d > 0 ? 'up' : 'down'); el.setAttribute('aria-hidden', 'true');
      el.textContent = (d > 0 ? '+' : '') + d;
      tile.appendChild(el); setTimeout(() => el.remove(), 1500);
    }
  }
  const aged = samePerson && lastAge !== null && P.age > lastAge;
  if (samePerson && P.alive && P.log.length > lastLogLen) { const snd = soundFor(P.log.slice(lastLogLen), aged); if (snd) SFX.play(snd); }
  lastLogLen = P.log.length;
  lastStats = { ...P.s }; lastId = P.id;
  renderLog();
  const ch = challengeOf(), goal = $('#goal');
  goal.hidden = !ch && !isHardcore();
  if (ch) goal.innerHTML = `<span aria-hidden="true">${ch.icon}</span> <b>${esc(ch.name)}</b> · ${P.challengeDone ? '<span class="ok">Complete ✓</span>' : P.challengeFailed ? '<span class="no">Failed</span>' : esc(ch.progress())}`;
  else if (isHardcore()) goal.innerHTML = '<span aria-hidden="true">💀</span> <b>Hardcore</b> · no rewinds, no editor';
  const left = maxActions() - P.actionsUsed;
  $('#actions-left').innerHTML = P.alive ? `<span class="pips" aria-hidden="true">${'●'.repeat(Math.max(0, left))}<i>${'●'.repeat(Math.max(0, P.actionsUsed))}</i></span>${left} of ${maxActions()} actions left` : '';
  $('#age-btn').disabled = !!pendingChoice;
  $('#age-btn').innerHTML = P.alive ? 'Age<br>+1' : 'New<br>life';
  $('#age-btn').setAttribute('aria-label', P.alive ? 'Age +1' : 'New life');
  if (pendingChoice) openChoice(); else if ($('#sheet').dataset.kind === 'choice') closeSheet();
}

// The story is grouped into one card per year, newest highlighted.
function renderLog() {
  const groups = []; let cur = null;
  for (const e of P.log.slice(-160)) {
    if (e.kind === 'year') { cur = { label: e.text, age: e.age, rows: [] }; groups.push(cur); continue; }
    if (!cur) { cur = { label: P.generation > 1 && e.age > 0 ? 'Earlier' : 'Birth', age: e.age, rows: [] }; groups.push(cur); }
    cur.rows.push(e);
  }
  const fresh = lastAge !== P.age; lastAge = P.age;
  // Fold runs of uneventful years (not the current one) into a single slim row.
  const view = [];
  groups.forEach((g, i) => {
    const prev = view[view.length - 1];
    if (!g.rows.length && i < groups.length - 1) {
      if (prev && prev.quiet) prev.to = g.age; else view.push({ quiet: true, from: g.age, to: g.age });
    } else view.push(g);
  });
  const L = $('#log');
  L.innerHTML = view.map((g, i) => {
    if (g.quiet) return `<div class="yr-quiet">${g.from === g.to ? `Age ${esc(g.from)}` : `Ages ${esc(g.from)}–${esc(g.to)}`} · quiet ${g.from === g.to ? 'year' : 'years'}</div>`;
    const now = i === view.length - 1;
    const rows = g.rows.length ? g.rows.map((e) => `<p class="ev ${esc(e.kind)}">${esc(e.text)}</p>`).join('') : '<p class="ev quiet">A quiet year.</p>';
    return `<article class="yr${now ? ' now' : ''}${now && fresh ? ' enter' : ''}"><div class="yr-badge" aria-hidden="true">${esc(g.age)}</div><div class="yr-body"><div class="yr-label">${esc(g.label)}</div>${rows}</div></article>`;
  }).join('');
  L.scrollTop = L.scrollHeight;
}

function sheet(kind, title, html) {
  if (kind !== 'chat') stopChat();
  const s = $('#sheet');
  s.dataset.kind = kind;
  $('#sheet-title').textContent = title;
  $('#sheet-body').innerHTML = html;
  s.hidden = false; $('#scrim').hidden = false;
  $('#sheet-close').hidden = kind === 'choice' || kind === 'death' || (kind === 'start' && (!P || !P.alive));
  const first = s.querySelector('button:not([hidden]), input, select');
  if (first) first.focus();
}
function closeSheet() {
  const s = $('#sheet');
  if (s.dataset.kind === 'choice' && pendingChoice) return;
  if (s.dataset.kind === 'death' && P && !P.alive) return;
  if (s.dataset.kind === 'start' && (!P || !P.alive)) return;
  stopChat();
  s.hidden = true; $('#scrim').hidden = true; s.dataset.kind = '';
  // Never leave the player on an empty board (e.g. closing the store from the start screen).
  if (!P) openStart(); else if (!P.alive) openDeath();
}

function btn(label, action, attrs = '', cls = '') { return `<button type="button" class="opt${cls ? ' ' + cls : ''}" data-act="${esc(action)}" ${attrs}>${esc(label)}</button>`; }

function openChoice() {
  if ($('#sheet').dataset.kind !== 'choice') SFX.play('choice');
  sheet('choice', 'Decision', `<div class="decision"><div class="big" aria-hidden="true">🤔</div><p class="prompt">${esc(pendingChoice.text)}</p></div>` + pendingChoice.options.map((o, i) => btn(o.label, `choice:${i}`)).join(''));
}

const ACT_ICONS = { 'Study': '📚', 'Work out': '🏋️', 'Meditate': '🧘', 'Party': '🎉', 'See a doctor': '🩺', 'Go on vacation': '✈️', 'Find love': '💘', 'Buy a lottery ticket': '🎟️', 'Shoplift': '🕶️' };
function openActivities() {
  if (!P.alive) return;
  const list = ACTIVITIES.filter((a) => P.age >= a.min && (!a.when || a.when()));
  const left = maxActions() - P.actionsUsed;
  const tiles = list.map((a) => {
    const m = a.label.match(/^(.*?)(?: \((.*)\))?$/);
    return `<button type="button" class="opt tile" data-act="act:${ACTIVITIES.indexOf(a)}" aria-label="${esc(a.label)}"><span class="ic" aria-hidden="true">${a.icon || ACT_ICONS[m[1]] || '🎯'}</span><span>${esc(m[1])}</span>${m[2] ? `<small>${esc(m[2])}</small>` : ''}</button>`;
  }).join('');
  sheet('acts', 'Activities', `<p class="note">${left} action${left === 1 ? '' : 's'} left this year.</p>` + (list.length ? `<div class="grid">${tiles}</div>` : '<p>You are too young for activities. Age up!</p>'));
}

function openCareer() {
  if (!P.alive) return;
  let h = '';
  const edu = Object.keys(P.edu).map((k) => EDU_LABEL[k]).join(', ') || 'None yet';
  h += `<div class="card"><div class="note">🎓 Education</div><b>${esc(edu)}</b>${P.school ? `<div class="note">Currently studying: ${esc(P.school === 'school' ? 'school' : EDU_LABEL[P.school] || P.school)}</div>` : ''}${P.debt ? `<div class="note">Debt: ${money(P.debt)}</div>` : ''}</div>`;
  if (P.job) {
    h += `<div class="card"><div class="note">💼 Current job</div><b>${esc(jobTitle())}</b><div class="note">${money(salary())}/year · ${P.job.years} yr${P.job.years === 1 ? '' : 's'}</div></div>`;
    h += btn('💪 Work harder (1 action)', 'work') + btn('Quit job', 'quit', '', 'ghost');
    if (P.age >= 60) h += btn('🏖️ Retire', 'retire');
  } else if (P.retired) {
    h += `<div class="card"><div class="note">🏖️ Retired</div><b>Pension ${money(P.pension)}/year</b></div>`;
  }
  if (P.age >= 22 && !P.edu.degree && !P.school) h += btn('🎓 Go back to university (4 years)', 'school');
  if (P.age >= 16 && !P.job) {
    h += '<h4>Job openings</h4>';
    const opts = CAREERS.filter((c) => (P.school === 'school' ? !c.edu && c.id !== 'music' : true));
    const free = opts.filter((c) => !c.pack), paid = opts.filter((c) => c.pack);
    const row = (c) => {
      const locked = c.pack && !owned[c.pack];
      const ok = eduOk(c.edu);
      const needs = [c.edu ? 'needs ' + EDU_LABEL[c.edu].toLowerCase() : '', c.hp ? 'fit' : '', c.looks ? 'good looks' : '', c.clean ? 'clean record' : ''].filter(Boolean).join(', ');
      const action = locked ? `<button type="button" class="opt" data-act="store:${esc(c.pack)}" style="width:auto">🔒 Unlock</button>`
        : ok ? btn('Apply', `apply:${c.id}`, 'style="width:auto" aria-label="Apply for ' + esc(c.ladder[0][0]) + ' (1 action)"') : '<span class="note">🔒 Not qualified</span>';
      return `<div class="job${locked ? ' locked' : ''}"><div><b>${c.icon ? c.icon + ' ' : ''}${esc(c.ladder[0][0])}</b><div class="note">${esc(c.name)} · ${money(c.ladder[0][1])}/yr${needs ? ' · ' + esc(needs) : ''}</div>${locked ? `<div class="note">Top job: ${esc(c.ladder[c.ladder.length - 1][0])}</div>` : ''}</div>${action}</div>`;
    };
    h += free.map(row).join('');
    if (paid.length) h += `<h4>⭐ Dream Jobs${owned.careers ? '' : ' · <button type="button" class="link" data-act="store:careers">unlock pack</button>'}</h4>` + paid.map(row).join('');
  } else if (P.age < 16) h += '<p class="note">You can look for work at 16.</p>';
  sheet('career', 'Career & education', h);
}

function openPeople() {
  let h = '';
  const groups = P.people.slice().sort((a, b) => (b.alive - a.alive));
  for (const x of groups) {
    const idx = P.people.indexOf(x);
    h += `<div class="person${x.alive ? '' : ' dead'}"><div class="pav" aria-hidden="true">${avatar(x)}</div><div><b>${esc(fullName(x))}</b><span class="rel">${esc(x.rel)}</span><div class="note">${x.alive ? 'Age ' + x.age + ' · bond ' + x.bond + '%' : 'Deceased'}</div>` +
      (x.alive ? `<div class="mini" aria-hidden="true"><span style="width:${x.bond}%"></span></div>` : '') + '</div>';
    if (x.alive && P.alive && !['Ex', 'Ex-spouse'].includes(x.rel)) {
      h += '<div class="row">' + btn('☕ Spend time', `time:${idx}`);
      if (x.rel === 'Partner' && P.age >= 18 && x.years >= 1) h += btn('💍 Propose', `propose:${idx}`);
      if (x.rel === 'Partner' || x.rel === 'Spouse') { h += btn(x.rel === 'Spouse' ? '💔 Divorce' : '💔 Break up', `break:${idx}`); }
      if (x.rel === 'Spouse' && P.age <= 60) h += btn('🍼 Try for a baby', `baby:${idx}`);
      h += '</div>';
    }
    h += '</div>';
  }
  sheet('people', 'Relationships', h || '<p>No one yet.</p>');
}

const SHOP_ICONS = { car: '🚗', home: '🏡' };
function openAssets() {
  let h = `<div class="kv"><div><small>Cash</small><b>${money(P.cash)}</b></div><div><small>Debt</small><b>${money(P.debt)}</b></div><div><small>Net worth</small><b>${money(netWorth())}</b></div></div>`;
  if (P.assets.length) { h += '<h4>You own</h4>'; P.assets.forEach((a, i) => { h += `<div class="job"><div><b>${SHOP_ICONS[a.kind] || '📦'} ${esc(a.name)}</b><div class="note">Worth ${money(a.value)}</div></div>${P.alive ? btn('Sell', `sell:${i}`, 'style="width:auto"') : ''}</div>`; }); }
  if (P.alive && P.age >= 18) { h += '<h4>Shop</h4>'; SHOP.forEach((s, i) => { h += `<div class="job"><div><b>${SHOP_ICONS[s.kind] || '📦'} ${esc(s.name)}</b><div class="note">${money(s.price)}${s.kind === 'home' ? ' · 20% deposit' : ''}</div></div>${btn('Buy', `buy:${i}`, 'style="width:auto"')}</div>`; }); }
  else if (P.alive) h += '<p class="note">You can buy things from age 18.</p>';
  sheet('assets', 'Money & assets', h);
}

function openEditor() {
  if (isHardcore()) { toast('The Destiny Editor is off in Hardcore mode.'); return; }
  if (!owned.editor) return openStore('editor');
  let h = '<p class="note">Rewrite your destiny. Drag to set each stat.</p>';
  const icons = { happy: '😊', health: '❤️', smarts: '🧠', looks: '✨' };
  for (const k of ['happy', 'health', 'smarts', 'looks']) h += `<label for="ed-${k}">${icons[k]} ${k[0].toUpperCase() + k.slice(1)} <output id="out-${k}">${P.s[k]}</output></label><input type="range" id="ed-${k}" min="0" max="100" value="${P.s[k]}">`;
  h += btn('Save', 'edsave', '', 'primary');
  sheet('editor', 'Destiny Editor', h);
  for (const k of ['happy', 'health', 'smarts', 'looks']) $(`#ed-${k}`).addEventListener('input', (e) => { $(`#out-${k}`).textContent = e.target.value; });
}

function openDeath() {
  const ach = P.achievements.map((a) => `<span>🏆 ${esc(ACHIEVEMENTS[a])}</span>`).join('');
  let h = `<div class="grave"><div class="big" aria-hidden="true">🪦</div><h3>${esc(fullName(P))}</h3><div class="note">Age ${P.age} · ${esc(P.causeOfDeath)}${P.mode && P.mode !== 'classic' ? ' · ' + MODES[P.mode].icon + ' ' + MODES[P.mode].name : ''}</div>
  ${challengeOf() ? `<div class="note">${challengeOf().icon} ${esc(challengeOf().name)}: ${P.challengeDone ? '<b class="ok">completed ✓</b>' : '<b class="no">not completed</b>'}</div>` : ''}
  <div class="kv"><div><small>Net worth</small><b>${money(netWorth())}</b></div><div><small>Career</small><b>${esc(P.job ? jobTitle() : P.retired ? 'Retired' : 'None')}</b></div><div><small>Kids</small><b>${kids().length}</b></div></div>
  ${ach ? `<div class="badges">${ach}</div>` : '<div class="note">No achievements this life.</div>'}</div>`;
  for (const k of livingKids()) h += btn(`${avatar(k)} Continue as ${k.first} (${k.rel.toLowerCase()}, age ${k.age})`, `heir:${P.people.indexOf(k)}`);
  if (history.length && !isHardcore()) h += owned.rewind ? btn('⏪ Second Chance: rewind up to 5 years', 'rewind') : btn('⏪ Second Chance: rewind time ⭐', 'store:rewind');
  h += btn('📖 Share this life in the Life stories room', 'sharelife');
  h += btn('Start a new life', 'newlife', '', 'primary');
  sheet('death', 'Rest in peace', h);
}

// ---------- start screen ----------
const HERO = '<div id="install-slot"></div><div class="hero"><div class="big" aria-hidden="true">🌍</div><h3>Live a whole life</h3><p class="note">Grow up, study, work, fall in love and leave a legacy, one year at a time.</p></div>';
let startMode = 'classic', startChallenge = CONTENT.challenges[0].id;
function modePicker() {
  const tiles = Object.entries(MODES).map(([k, m]) => `<button type="button" class="opt tile mode-tile" data-act="mode:${k}" aria-pressed="${k === startMode}"><span class="ic" aria-hidden="true">${m.icon}</span><span>${esc(m.name)}</span></button>`).join('');
  const done = doneChallenges();
  const ch = CONTENT.challenges.map((c) => `<option value="${c.id}"${c.id === startChallenge ? ' selected' : ''}>${c.icon} ${esc(c.name)}${done.includes(c.id) ? ' ✓' : ''}</option>`).join('');
  return `<h4>Game mode</h4><div class="grid" role="group" aria-label="Game mode">${tiles}</div><p id="mode-desc" class="note">${esc(MODES[startMode].desc)}</p>
    <div id="ch-pick"${startMode === 'challenge' ? '' : ' hidden'}><label for="st-challenge">Challenge</label><select id="st-challenge">${ch}</select><p id="ch-desc" class="note">${esc(CONTENT.challenges.find((c) => c.id === startChallenge).desc)}</p></div>`;
}
function setMode(m) {
  if (!MODES[m]) return;
  startMode = m;
  document.querySelectorAll('.mode-tile').forEach((t) => t.setAttribute('aria-pressed', t.dataset.act === 'mode:' + m));
  $('#mode-desc').textContent = MODES[m].desc;
  $('#ch-pick').hidden = m !== 'challenge';
}
function doneChallenges() { try { return JSON.parse(localStorage.getItem('lt_challenges') || '[]'); } catch (e) { return []; } }

function openStart() {
  const countries = Object.keys(COUNTRIES);
  if (!owned.plus) {
    sheet('start', 'A new life', `${HERO}${modePicker()}<div style="height:.6rem"></div>${btn('👶 Be born', 'born', '', 'primary')}<div class="two">${btn('⭐ Store', 'store:', '', 'ghost')}${btn('💬 Chat rooms', 'rooms', '', 'ghost')}</div>
      <p class="note" style="text-align:center">You'll be born somewhere random. Want to pick your name, country and gender? That's part of <button type="button" class="link" data-act="store:plus">Lifetimes Plus</button>.</p>`);
  } else {
    sheet('start', 'A new life', `${HERO}${modePicker()}<h4>Who you'll be</h4><label for="st-first">First name</label><input id="st-first" maxlength="20" placeholder="Random">
    <label for="st-last">Last name</label><input id="st-last" maxlength="24" placeholder="Random">
    <label for="st-gender">Gender</label><select id="st-gender"><option value="">Random</option><option value="f">Female</option><option value="m">Male</option></select>
    <label for="st-country">Country</label><select id="st-country"><option value="">Random</option>${countries.map((c) => `<option value="${esc(c)}">${FLAGS[c] || ''} ${esc(c)}</option>`).join('')}</select>
    <div style="height:.6rem"></div>${btn('👶 Be born', 'born-plus', '', 'primary')}<div class="two">${btn('⭐ Store', 'store:', '', 'ghost')}${btn('💬 Chat rooms', 'rooms', '', 'ghost')}</div>`);
  }
  if (typeof Install !== 'undefined') Install.refresh();
  $('#st-challenge').addEventListener('change', (e) => { startChallenge = e.target.value; $('#ch-desc').textContent = CONTENT.challenges.find((c) => c.id === startChallenge).desc; });
}

function born(custom) {
  const o = {};
  if (custom) {
    const f = $('#st-first').value.trim(), l = $('#st-last').value.trim(), g = $('#st-gender').value, c = $('#st-country').value;
    if (f) o.first = f.slice(0, 20); if (l) o.last = l.slice(0, 24); if (g) o.gender = g; if (c && COUNTRIES[c]) o.country = c;
  }
  const ch = startMode === 'challenge' ? CONTENT.challenges.find((c) => c.id === startChallenge) : null;
  if (startMode === 'hardcore') o.wealth = pick([0, 0, 1]);
  if (ch && ch.wealth !== undefined) o.wealth = ch.wealth;
  P = newPerson(o); history = []; pendingChoice = null;
  P.mode = startMode; P.challenge = ch ? ch.id : null;
  const w = ['a struggling', 'a working-class', 'a comfortable middle-class', 'a wealthy'][P.wealth];
  log(`You were born a ${P.gender === 'm' ? 'boy' : 'girl'} in ${P.country} to ${w} family.`);
  const mom = P.people[0], dad = P.people[1];
  log(`Your mother is ${fullName(mom)} (${mom.age}) and your father is ${fullName(dad)} (${dad.age}).`);
  if (ch) log(`Challenge: ${ch.name}. ${ch.desc}`, 'hint');
  if (P.mode === 'hardcore') log('Hardcore mode: no rewinds, no Destiny Editor. Good luck.', 'hint');
  closeSheet(); save(); render(); SFX.play('birth');
}

// Challenge progress is checked whenever the game saves (after every year, action and decision).
function checkChallenge() {
  const ch = challengeOf();
  if (!ch || P.challengeDone || P.challengeFailed) return;
  if (ch.done()) {
    P.challengeDone = true;
    log(`🎯 Challenge complete: ${ch.name}!`, 'good');
    unlock('challenge');
    const d = doneChallenges(); if (!d.includes(ch.id)) { d.push(ch.id); localStorage.setItem('lt_challenges', JSON.stringify(d)); }
    toast(`🎯 Challenge complete: ${ch.name}!`, true);
  } else if ((ch.fail && ch.fail()) || !P.alive) {
    P.challengeFailed = true;
    log(`Challenge failed: ${ch.name}.`, 'bad');
  }
}

// ---------- store (in-app purchases) ----------
let storeConfig = { checkout: {}, prices: {} };

const PACK_ICONS = { plus: '⚡', editor: '🔮', rewind: '⏪', careers: '🚀', drama: '🎭' };
function openStore(focus) {
  let h = '<div class="pledge"><b>🤝 Fair Price Pledge</b><p class="note">Every pack is a one-time purchase. Buying everything costs under $12, with no subscriptions, no pay-per-use rewinds and no choices locked behind ads. The base game is complete and free. Purchases stay on this device; use "Restore" with your license key on another.</p></div>';
  for (const [k, p] of Object.entries(PACKS)) {
    const url = storeConfig.checkout[k];
    h += `<div class="pack${focus === k ? ' focus' : ''}"><div class="pic" aria-hidden="true">${PACK_ICONS[k]}</div><div class="pinfo"><b>${esc(p.name)}</b>${storeConfig.prices[k] ? `<span class="price">${esc(storeConfig.prices[k])}</span>` : ''}<p class="note">${esc(p.blurb)}</p></div>` +
      (owned[k] ? '<span class="owned">Owned ✓</span>' : url ? `<a class="buy" href="${esc(url)}" rel="noopener">Buy</a>` : '<span class="note">Soon</span>') + '</div>';
  }
  h += `<h4>Restore a purchase</h4><label for="lk">License key (from your receipt email)</label><input id="lk" autocomplete="off" spellcheck="false">${btn('Restore', 'restore', '', 'ghost')}<p id="lk-msg" role="status"></p>`;
  sheet('store', 'Store', h);
}

function keys() { try { return JSON.parse(localStorage.getItem('lt_keys') || '[]'); } catch (e) { return []; } }

async function redeem(key, quiet) {
  const r = await fetch('/api/unlock', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) { if (!quiet) toast(j.error || 'Could not verify that key.'); return false; }
  for (const p of j.packs || []) if (p in owned) owned[p] = true;
  const ks = keys(); if (!ks.includes(key)) { ks.push(key); localStorage.setItem('lt_keys', JSON.stringify(ks)); }
  localStorage.setItem('lt_owned', JSON.stringify(owned));
  if (!quiet) SFX.play('achievement');
  if (!quiet) toast(`Unlocked: ${(j.packs || []).map((p) => PACKS[p]?.name).join(', ')}. Thank you!`, true);
  return true;
}

async function initStore() {
  try { Object.assign(owned, JSON.parse(localStorage.getItem('lt_owned') || '{}')); } catch (e) { /* ignore */ }
  try { const r = await fetch('/api/config'); if (r.ok) storeConfig = await r.json(); } catch (e) { /* offline: store shows "coming soon" */ }
  // Lemon Squeezy can send buyers back to /?key=[license_key] after checkout.
  const url = new URL(location.href);
  const k = url.searchParams.get('key');
  if (k) { url.searchParams.delete('key'); history_replace(url); await redeem(k, false); render(); }
}
function history_replace(url) { window.history.replaceState(null, '', url.pathname + (url.search || '') + url.hash); }

// ---------- chat rooms ----------
// Public rooms on our own server. Everything a stranger sends is rendered with esc(), never as HTML.
const chat = { room: 'general', lastId: 0, timer: null, mine: new Set(), reported: new Set(), life: null, rooms: [] };
function nick() { return (localStorage.getItem('lt_nick') || '').slice(0, 16); }
function stopChat() { clearInterval(chat.timer); chat.timer = null; }
function ago(ts) { const s = Math.max(0, Date.now() / 1000 - ts); return s < 60 ? 'now' : s < 3600 ? Math.floor(s / 60) + 'm' : Math.floor(s / 3600) + 'h'; }

function lifeCard(l) {
  const mode = l.mode && l.mode !== 'classic' ? ` · ${MODES[l.mode] ? MODES[l.mode].icon + ' ' + MODES[l.mode].name : ''}` : '';
  return `<div class="lifecard"><div class="lc-top">🪦 <b>${esc(l.name)}</b> <span class="note">${esc(l.age)} · ${esc(l.country)}${esc(mode)}</span></div>
    <div class="note">${l.career ? esc(l.career) + ' · ' : ''}${money(l.worth)} · ${esc(l.achievements)} 🏆${l.cause ? ' · ' + esc(l.cause) : ''}</div></div>`;
}

function openRooms(room, life) {
  if (room && CHAT_ROOMS_FALLBACK.some((r) => r.id === room)) chat.room = room;
  if (life !== undefined) chat.life = life;
  const n = nick();
  sheet('chat', 'Chat rooms', `<div class="rooms" role="tablist" aria-label="Rooms">${(chat.rooms.length ? chat.rooms : CHAT_ROOMS_FALLBACK).map(roomChip).join('')}</div>
    <p id="room-blurb" class="note"></p>
    <div id="chat-list" class="chat-list" aria-live="polite" aria-label="Messages"><p class="note">Loading…</p></div>
    <div id="chat-card"></div>
    <form id="chat-form" class="chat-form" autocomplete="off">
      <div id="nick-row"${n ? ' hidden' : ''}><label for="chat-nick">Nickname</label><input id="chat-nick" maxlength="16" value="${esc(n)}" placeholder="2-16 letters or numbers"></div>
      <div id="as-row" class="note"${n ? '' : ' hidden'}>Chatting as <b id="as-nick">${esc(n)}</b> · <button type="button" class="link" data-act="nick-change">change</button></div>
      <div class="send-row"><label for="chat-text" class="sr">Message</label><input id="chat-text" maxlength="240" placeholder="Say something…"><button type="submit" class="opt primary send">Send</button></div>
      <p id="chat-err" class="no" role="status"></p>
    </form>
    <p class="note">Be kind. No links, emails or phone numbers. Messages disappear after 24 hours. Tap ⚑ to report; reported messages are hidden.</p>`);
  $('#chat-form').addEventListener('submit', (e) => { e.preventDefault(); sendChat(); });
  if (chat.life && !$('#chat-text').value) $('#chat-text').value = `Here's how my life as ${chat.life.name} went.`;
  showRoom();
  fetch('/api/rooms').then((r) => r.json()).then((j) => { chat.rooms = j.rooms || []; document.querySelector('.rooms') && (document.querySelector('.rooms').innerHTML = chat.rooms.map(roomChip).join('')); showRoom(true); }).catch(() => {});
  stopChat();
  chat.timer = setInterval(() => { if (!document.hidden) pollChat(); }, 4000);
}
const CHAT_ROOMS_FALLBACK = [{ id: 'general', icon: '💬', name: 'General' }, { id: 'stories', icon: '📖', name: 'Life stories' }, { id: 'rich', icon: '💰', name: 'Billionaires club' }, { id: 'hardcore', icon: '💀', name: 'Hardcore' }, { id: 'help', icon: '🛟', name: 'Help & tips' }];
function roomChip(r) { return `<button type="button" class="chip" role="tab" data-act="room:${esc(r.id)}" aria-selected="${r.id === chat.room}">${esc(r.icon)} ${esc(r.name)}${r.active ? ` <span class="dot" aria-label="${esc(r.active)} active">${esc(r.active)}</span>` : ''}</button>`; }

function showRoom(keepList) {
  document.querySelectorAll('.rooms .chip').forEach((c) => c.setAttribute('aria-selected', c.dataset.act === 'room:' + chat.room));
  const r = chat.rooms.find((x) => x.id === chat.room);
  if ($('#room-blurb')) $('#room-blurb').textContent = r ? r.blurb : '';
  $('#chat-card').innerHTML = chat.life ? `<div class="attach">${lifeCard(chat.life)}<button type="button" class="link" data-act="chatcard-x">Don't attach</button></div>` : '';
  if (!keepList) { chat.lastId = 0; $('#chat-list').innerHTML = ''; pollChat(); }
}

async function pollChat() {
  const room = chat.room;
  let j;
  try { const r = await fetch(`/api/rooms/${encodeURIComponent(room)}/messages?after=${chat.lastId}`); if (!r.ok) return; j = await r.json(); } catch (e) { return; }
  const L = $('#chat-list');
  if (!L || room !== chat.room) return;
  const fresh = (j.messages || []).filter((m) => m.id > chat.lastId && !chat.reported.has(m.id));
  if (!chat.lastId && !fresh.length) L.innerHTML = '<p class="note empty">No messages yet. Say hi!</p>';
  if (!fresh.length) return;
  const wasLoaded = chat.lastId > 0;
  L.querySelector('.empty')?.remove();
  const atBottom = L.scrollHeight - L.scrollTop - L.clientHeight < 60;
  L.insertAdjacentHTML('beforeend', fresh.map((m) => {
    const me = chat.mine.has(m.id);
    return `<div class="msg${me ? ' mine' : ''}" data-id="${m.id}"><div class="mhead"><b>${esc(m.nick)}</b> <span class="note">${ago(m.ts)}</span>${me ? '' : `<button type="button" class="flag" data-act="report:${m.id}" aria-label="Report message from ${esc(m.nick)}">⚑</button>`}</div><div class="mtext">${esc(m.text)}</div>${m.life ? lifeCard(m.life) : ''}</div>`;
  }).join(''));
  chat.lastId = Math.max(chat.lastId, ...fresh.map((m) => m.id));
  if (atBottom || fresh.some((m) => chat.mine.has(m.id))) L.scrollTop = L.scrollHeight;
  if (wasLoaded && fresh.some((m) => !chat.mine.has(m.id))) SFX.play('chat');
}

async function sendChat() {
  const err = $('#chat-err'); err.textContent = '';
  const n = (nick() || $('#chat-nick').value).trim();
  const text = $('#chat-text').value.trim();
  if (!n) { err.textContent = 'Pick a nickname first.'; $('#chat-nick').focus(); return; }
  if (!text) return;
  const body = { nick: n, text };
  if (chat.life) body.life = chat.life;
  let r, j = {};
  try { r = await fetch(`/api/rooms/${encodeURIComponent(chat.room)}/messages`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); j = await r.json().catch(() => ({})); } catch (e) { err.textContent = 'Could not send. Check your connection.'; return; }
  if (!r.ok) { err.textContent = j.error || 'Could not send.'; SFX.play('error'); return; }
  localStorage.setItem('lt_nick', n);
  $('#nick-row').hidden = true; $('#as-row').hidden = false; $('#as-nick').textContent = n;
  chat.mine.add(j.message.id); chat.life = null; $('#chat-card').innerHTML = '';
  $('#chat-text').value = ''; $('#chat-text').focus();
  pollChat();
}

async function reportMsg(id) {
  chat.reported.add(id);
  document.querySelector(`.msg[data-id="${id}"]`)?.remove();
  toast('Thanks. The message is hidden for you, and it is hidden for everyone if others report it too.');
  try { await fetch(`/api/rooms/${encodeURIComponent(chat.room)}/messages/${id}/report`, { method: 'POST' }); } catch (e) { /* best effort */ }
}

function shareLife() {
  openRooms('stories', {
    name: fullName(P), age: P.age, country: P.country, career: P.job ? jobTitle() : P.retired ? 'Retired' : '',
    cause: P.causeOfDeath || '', worth: Math.round(netWorth()), achievements: P.achievements.length, mode: P.mode || 'classic',
  });
}

// ---------- toast ----------
let toastTimer;
function toast(t, quiet) {
  if (!quiet) SFX.play('tap'); const el = $('#toast'); el.textContent = t; el.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 3500); }

// ---------- wiring ----------
document.addEventListener('click', (e) => {
  const b = e.target.closest('[data-act]'); if (!b) return;
  const [a, arg] = b.dataset.act.split(':');
  const i = Number(arg);
  switch (a) {
    case 'choice': return resolveChoice(i);
    case 'act': return doAction(ACTIVITIES[i].run);
    case 'apply': return applyFor(careerById(arg));
    case 'work': return workHarder();
    case 'quit': return quitJob();
    case 'retire': return retire();
    case 'school': return backToSchool();
    case 'time': return spendTime(P.people[i]);
    case 'propose': return propose(P.people[i]);
    case 'break': return breakUp(P.people[i]);
    case 'baby': return tryForBaby(P.people[i]);
    case 'buy': return buy(SHOP[i]);
    case 'sell': return sell(i);
    case 'heir': return continueAs(P.people[i]);
    case 'rewind': return rewind();
    case 'newlife': closeSheet(); return openStart();
    case 'born': return born(false);
    case 'born-plus': return born(true);
    case 'store': return openStore(arg);
    case 'mode': SFX.play('tap'); return setMode(arg);
    case 'rooms': return openRooms();
    case 'install': return Install.prompt();
    case 'install-x': return Install.dismiss();
    case 'room': chat.room = arg; return showRoom();
    case 'report': return reportMsg(i);
    case 'sharelife': return shareLife();
    case 'chatcard-x': chat.life = null; return showRoom(true);
    case 'nick-change': localStorage.removeItem('lt_nick'); $('#nick-row').hidden = false; $('#as-row').hidden = true; return $('#chat-nick').focus();
    case 'restore': { const k = $('#lk').value.trim(); if (k) redeem(k, false).then((ok) => { if (ok) openStore(); }); return; }
    case 'edsave': for (const k of ['happy', 'health', 'smarts', 'looks']) P.s[k] = clamp(Number($(`#ed-${k}`).value)); log('You rewrote your destiny.'); closeSheet(); save(); return render();
  }
});

$('#age-btn').addEventListener('click', () => (P && !P.alive ? openDeath() : ageUp()));
$('#nav-acts').addEventListener('click', () => { SFX.play('tap'); openActivities(); });
$('#nav-career').addEventListener('click', () => { SFX.play('tap'); openCareer(); });
$('#nav-people').addEventListener('click', () => { SFX.play('tap'); openPeople(); });
$('#nav-assets').addEventListener('click', () => { SFX.play('tap'); openAssets(); });
$('#nav-editor').addEventListener('click', openEditor);
$('#nav-store').addEventListener('click', () => openStore());
$('#nav-rooms').addEventListener('click', () => openRooms());
function syncSoundBtn() { const b = $('#nav-sound'); b.textContent = SFX.muted ? '🔇' : '🔊'; b.setAttribute('aria-pressed', String(!SFX.muted)); b.setAttribute('aria-label', SFX.muted ? 'Sound off' : 'Sound on'); }
$('#nav-sound').addEventListener('click', () => { SFX.toggle(); syncSoundBtn(); });
syncSoundBtn();
$('#sheet-close').addEventListener('click', closeSheet);
$('#scrim').addEventListener('click', closeSheet);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSheet(); });

(async function main() {
  await initStore();
  if (load()) { render(); if (!P.alive) openDeath(); } else openStart();
})();

// exposed for the automated play test
window.__lt = { get P() { return P; }, get pending() { return pendingChoice; }, ageUp, resolveChoice, owned };
