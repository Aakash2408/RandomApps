// Lifetimes: extra content, merged into the base lists by game.js.
// Loaded BEFORE game.js; functions here run later, so they can use game.js helpers
// (P, bump, chance, pick, rnd, money, salary, partner, livingKids, ...).
// Entries with `pack` need that in-app purchase; everything else is free.
'use strict';

const CONTENT = {
  // ---------------------------------------------------------------- careers
  // sm = smarts needed, hp = health needed, looks = looks needed, clean = no criminal record.
  careers: [
    { id: 'chef', name: 'Kitchen', edu: null, sm: 0, ladder: [['Line Cook', 24000], ['Sous Chef', 40000], ['Head Chef', 68000], ['Celebrity Chef', 320000]], top: 'celebchef',
      lines: ['Dinner rush every night. Your knife skills are getting scary good.', 'A food critic loved your risotto.', 'You burned yourself on the grill. Again.'] },
    { id: 'police', name: 'Police', edu: 'hs', sm: 25, hp: 45, clean: true, ladder: [['Police Officer', 46000], ['Sergeant', 62000], ['Lieutenant', 80000], ['Police Chief', 140000]],
      lines: ['You worked a string of night shifts.', 'You helped return a lost child to their parents.', 'Paperwork. So much paperwork.'] },
    { id: 'fire', name: 'Fire service', edu: 'hs', sm: 15, hp: 60, ladder: [['Firefighter', 44000], ['Engineer', 58000], ['Captain', 76000], ['Fire Chief', 125000]],
      lines: ['You pulled a family out of a burning house.', 'You got a cat out of a tree. It was not grateful.', 'Long shifts, good crew.'] },
    { id: 'realty', name: 'Real estate', edu: 'hs', sm: 30, ladder: [['Rental Agent', 30000], ['Realtor', 62000], ['Top Producer', 150000], ['Brokerage Owner', 310000]],
      lines: ['You sold a house with a "charming" leaky roof.', 'Open houses every weekend.'] },
    { id: 'acct', name: 'Accounting', edu: 'degree', sm: 50, ladder: [['Junior Accountant', 52000], ['Accountant', 72000], ['Senior Accountant', 96000], ['CFO', 260000]],
      lines: ['Tax season ate your whole spring.', 'You found a $40,000 mistake in a client\'s books.'] },

    // Dream Jobs pack
    { id: 'astro', pack: 'careers', icon: '🚀', name: 'Space agency', edu: 'degree', sm: 80, hp: 70, ladder: [['Astronaut Candidate', 70000], ['Astronaut', 115000], ['Mission Commander', 175000], ['Moonwalker', 260000]], top: 'astronaut',
      lines: ['You spent weeks in a centrifuge. Your lunch did not stay down.', 'Zero-g training was the best day of your life.', 'You watched Earth rise from orbit.'] },
    { id: 'athlete', pack: 'careers', icon: '🏅', name: 'Pro sports', edu: null, sm: 0, hp: 78, ladder: [['Rookie', 60000], ['Starter', 400000], ['All-Star', 2200000], ['Sports Legend', 9000000]], top: 'legend', maxAge: 38,
      lines: ['You scored the winning goal in front of 60,000 fans.', 'A sports drink wants you in its ads.', 'You tweaked your hamstring in training.'] },
    { id: 'pilot', pack: 'careers', icon: '✈️', name: 'Aviation', edu: 'degree', sm: 55, hp: 55, ladder: [['First Officer', 78000], ['Captain', 160000], ['Chief Pilot', 240000]],
      lines: ['You landed in a crosswind and the cabin clapped.', 'Layovers in five countries this year.'] },
    { id: 'stream', pack: 'careers', icon: '🎥', name: 'Content creation', edu: null, sm: 0, looks: 35, ladder: [['Small Streamer', 6000], ['Partnered Creator', 48000], ['Top Creator', 380000], ['Internet Icon', 2400000]], top: 'icon',
      lines: ['A clip of you went viral overnight.', 'Your chat spammed the same emote for an hour.', 'A brand deal paid for your new setup.'] },
    { id: 'politics', pack: 'careers', icon: '🏛️', name: 'Politics', edu: 'degree', sm: 55, clean: true, ladder: [['City Councillor', 52000], ['Mayor', 120000], ['Senator', 175000], ['Head of State', 400000]], top: 'leader',
      lines: ['You kissed a lot of babies on the campaign trail.', 'A rival dug up your old social media posts.', 'You cut the ribbon on a new hospital.'] },
    { id: 'detective', pack: 'careers', icon: '🕵️', name: 'Investigations', edu: 'hs', sm: 55, clean: true, ladder: [['Private Investigator', 42000], ['Detective', 78000], ['Lead Detective', 110000], ['Legendary Sleuth', 210000]],
      lines: ['You cracked a ten-year-old cold case.', 'Stakeouts mostly involve bad coffee.'] },
    { id: 'fashion', pack: 'careers', icon: '👗', name: 'Fashion', edu: 'degree', sm: 30, looks: 50, ladder: [['Design Intern', 26000], ['Designer', 70000], ['Creative Director', 210000], ['Fashion Icon', 1500000]], top: 'fashionicon',
      lines: ['Your collection walked the runway in Paris.', 'A celebrity wore your dress to an awards show.'] },
    { id: 'gamedev', pack: 'careers', icon: '🎮', name: 'Game studios', edu: 'degree', sm: 55, ladder: [['QA Tester', 38000], ['Game Developer', 85000], ['Lead Designer', 150000], ['Studio Founder', 950000]], top: 'founder',
      lines: ['Crunch time. You slept under your desk.', 'Players found a bug that became a beloved feature.', 'Your game hit #1 on the store.'] },
  ],

  achievements: {
    celebchef: 'Became a celebrity chef', astronaut: 'Walked on the moon', legend: 'Became a sports legend', icon: 'Became an internet icon',
    leader: 'Led a nation', fashionicon: 'Became a fashion icon', founder: 'Founded a hit game studio', hardcore80: 'Hardcore: lived to 80',
    challenge: 'Completed a challenge', famous: 'Became famous', hero: 'Did something heroic', petparent: 'Adopted a pet',
  },

  // ---------------------------------------------------------------- activities
  activities: [
    { label: 'Read a book', icon: '📖', min: 6, run: () => (bump('smarts', rnd(1, 4)), bump('happy', 1), `You read ${pick(['a mystery novel', 'a biography', 'a sci-fi epic', 'a book about money', 'a graphic novel'])}.`) },
    { label: 'Learn a language', icon: '🗣️', min: 10, run: () => (bump('smarts', rnd(2, 5)), `You practised ${pick(['Spanish', 'Japanese', 'Arabic', 'French', 'Hindi', 'Portuguese'])} every day.`) },
    { label: 'Volunteer', icon: '🤝', min: 12, run: () => { bump('happy', rnd(3, 6)); P.karma = (P.karma || 0) + 1; return pick(['You volunteered at a food bank.', 'You cleaned up a beach with strangers.', 'You read to kids at the library.']); } },
    { label: 'Adopt a pet ($500)', icon: '🐶', min: 18, when: () => !P.pet && P.cash >= 500, run: () => { P.cash -= 500; P.pet = pick(['dog', 'cat', 'rabbit', 'parrot']); bump('happy', 10); unlock('petparent'); return `You adopted a ${P.pet}. You named it ${pick(['Biscuit', 'Mango', 'Pixel', 'Noodle', 'Captain', 'Pepper'])}.`; } },
    { label: 'Cosmetic surgery ($6,000)', icon: '💉', min: 18, when: () => P.cash >= 6000, run: () => { P.cash -= 6000; if (chance(0.82)) { bump('looks', rnd(6, 14)); return 'The surgery went well. You look great.'; } bump('looks', -rnd(4, 10)); bump('happy', -6); return 'The surgery went badly. You regret it.'; } },
  ],

  // ---------------------------------------------------------------- passive events
  passive: [
    { min: 5, max: 9, p: 0.15, run: () => (bump('happy', 2), 'You lost a tooth and the tooth fairy left you a coin.') },
    { min: 8, max: 15, p: 0.06, when: () => P.s.smarts > 60, run: () => (bump('happy', 5), bump('smarts', 2), 'You won the school spelling bee!') },
    { min: 16, max: 19, p: 0.18, run: () => (bump('happy', 4), chance(0.25) ? 'You passed your driving test on the third try.' : 'You passed your driving test!') },
    { min: 18, max: 80, p: 0.05, when: () => P.assets.some((a) => a.kind === 'car'), run: () => { P.cash -= 150; bump('happy', -2); return 'You got a $150 speeding ticket.'; } },
    { min: 22, max: 65, p: 0.07, when: () => !!P.job, run: () => { const b = Math.round(salary() * 0.08); P.cash += b; bump('happy', 4); return `You got a ${money(b)} bonus at work.`; } },
    { min: 18, max: 90, p: 0.06, run: () => { const r = rnd(200, 1200); P.cash += r; return `You got a ${money(r)} tax refund.`; } },
    { min: 18, max: 90, p: 0.03, when: () => !!P.pet, run: () => { P.cash -= 900; bump('happy', -2); return `Your ${P.pet} ate something it shouldn't have. The vet bill was $900.`; } },
    { min: 30, max: 90, p: 0.04, run: () => (bump('happy', 5), pick(['An old friend got back in touch.', 'You reconnected with your childhood best friend.'])) },
    // Life Drama pack
    { pack: 'drama', min: 12, max: 90, p: 0.008, run: () => { bump('health', -20); return 'You were struck by lightning. You survived, and your hair will never be the same.'; } },
    { pack: 'drama', min: 18, max: 90, p: 0.03, run: () => { const w = rnd(2, 20) * 500; P.cash += w; bump('happy', 6); return `You won ${money(w)} in a radio phone-in contest.`; } },
    { pack: 'drama', min: 18, max: 90, p: 0.02, when: () => P.assets.some((a) => a.kind === 'car'), run: () => { P.cash += 15000; return 'A meteorite crushed your car. A collector paid $15,000 for the rock.'; } },
    { pack: 'drama', min: 20, max: 85, p: 0.03, run: () => { const l = Math.min(P.cash, rnd(1000, 6000)); P.cash -= l; bump('happy', -5); return `Your identity was stolen. You lost ${money(l)} before the bank froze your account.`; } },
  ],

  // ---------------------------------------------------------------- decisions
  choices: [
    { min: 9, max: 16, p: 0.08, text: () => 'You find a muddy, shivering puppy behind school.', options: [
      { label: 'Bring it home', run: () => (chance(0.6) ? (P.pet = 'dog', bump('happy', 8), 'Your parents caved. The puppy is now family.') : (bump('happy', -3), 'Your parents said no. You cried.')) },
      { label: 'Take it to a shelter', run: () => (bump('happy', 3), 'The shelter found it a home within a week.') },
    ] },
    { min: 17, max: 17, p: 0.6, text: () => "It's prom season.", options: [
      { label: 'Ask your crush', run: () => (chance(0.3 + P.s.looks / 200) ? (bump('happy', 10), 'They said yes! Best night of high school.') : (bump('happy', -6), 'They said no. You went with friends anyway.')) },
      { label: 'Go with friends', run: () => (bump('happy', 5), 'You danced badly and loved it.') },
      { label: 'Skip it', run: () => 'You stayed home and played video games.' },
    ] },
    { min: 18, max: 32, p: 0.06, text: () => "Your roommate hasn't paid their share of rent in three months.", options: [
      { label: 'Confront them', run: () => (chance(0.5) ? 'They paid up, grumbling.' : (bump('happy', -4), 'They moved out in the night. You covered it.')) },
      { label: 'Cover for them', run: () => { P.cash -= 1800; bump('happy', -2); return 'You paid $1,800 to keep the peace.'; } },
      { label: 'Move out', run: () => (bump('happy', 3), 'You found a smaller place on your own.') },
    ] },
    { min: 20, max: 70, p: 0.04, text: () => "You've been called for jury duty.", options: [
      { label: 'Serve', run: () => (bump('smarts', 2), pick(['It was a dull fraud case.', 'It was a dramatic murder trial. You couldn\'t sleep for weeks.'])) },
      { label: 'Try to get out of it', run: () => (chance(0.5) ? 'You got excused.' : (bump('happy', -3), 'The judge was not amused. You served anyway.')) },
    ] },
    { min: 22, max: 65, p: 0.05, when: () => !!P.job, text: () => 'Your boss asks you to take the blame for their mistake.', options: [
      { label: 'Take the fall', run: () => (P.perf -= 1.5, chance(0.5) ? (P.perf += 3, 'Your boss owes you one. A promotion feels closer.') : (bump('happy', -5), 'Your boss forgot all about it.')) },
      { label: 'Refuse', run: () => (chance(0.7) ? (bump('happy', 3), 'You stood your ground. Respect.') : (P.perf -= 2, bump('happy', -4), 'Your boss started making your life difficult.')) },
    ] },
    { min: 24, max: 70, p: 0.04, when: () => P.cash >= 2500, text: () => 'A close friend is getting married abroad. The trip would cost $2,500.', options: [
      { label: 'Go', run: () => { P.cash -= 2500; bump('happy', 8); return 'You danced at the wedding until sunrise.'; } },
      { label: 'Send a gift instead', run: () => { P.cash -= 150; bump('happy', -2); return 'You sent a nice gift and watched the video.'; } },
    ] },
    { min: 40, max: 58, p: 0.06, text: () => "You're having a midlife crisis.", options: [
      { label: 'Buy a sports car ($60,000)', run: () => { if (P.cash < 60000) return 'You looked at sports cars online, then closed the tab.'; P.cash -= 60000; P.assets.push({ name: 'Sports car', kind: 'car', value: 60000 }); bump('happy', 12); return 'You bought a red sports car. Your back hurts getting in.'; } },
      { label: 'Run a marathon', run: () => (bump('health', 8), bump('happy', 6), 'You trained for six months and finished your first marathon.') },
      { label: 'See a therapist', run: () => { P.cash -= 1500; bump('happy', 10); return 'Therapy helped more than a car would have.'; } },
    ] },
    { min: 65, max: 95, p: 0.06, text: () => 'A caller says your grandchild is in jail and needs $5,000 bail, today.', options: [
      { label: 'Send the money', run: () => { const l = Math.min(P.cash, 5000); P.cash -= l; bump('happy', -8); return `It was a scam. You lost ${money(l)}.`; } },
      { label: 'Hang up and call family', run: () => (bump('smarts', 2), 'It was a scam. Your grandchild was fine, at home playing games.') },
    ] },

    // Life Drama pack
    { pack: 'drama', min: 18, max: 55, p: 0.05, text: () => 'A reality TV show wants you to audition.', options: [
      { label: 'Audition', run: () => { if (chance(0.25 + P.s.looks / 300)) { P.cash += 75000; bump('happy', 12); P.fame = (P.fame || 0) + 30; unlock('famous'); return 'You made the show, and won! $75,000 and a lot of fans.'; } bump('happy', -6); return 'You made the show and were voted off first. The memes live forever.'; } },
      { label: 'No way', run: () => 'You kept your dignity.' },
    ] },
    { pack: 'drama', min: 20, max: 70, p: 0.04, text: () => 'Someone claiming to be your long-lost sibling knocks on your door.', options: [
      { label: 'Welcome them in', run: () => { const c = COUNTRIES[P.country]; const g = pick(['m', 'f']); P.people.push(person(pick(c[g]), P.last, g, g === 'm' ? 'Brother' : 'Sister', Math.max(1, P.age + rnd(-8, 8)), rnd(30, 60))); bump('happy', 8); return 'It was true. You have a whole new sibling.'; } },
      { label: 'Ask for a DNA test', run: () => (chance(0.5) ? (bump('happy', 4), 'The test was positive. You are cautiously getting to know each other.') : 'The test was negative. It was a scam.') },
      { label: 'Close the door', run: () => (bump('happy', -2), 'You never found out the truth.') },
    ] },
    { pack: 'drama', min: 25, max: 75, p: 0.03, text: () => 'A creepy old mansion is on sale for just $90,000. Locals say it is haunted.', when: () => P.cash >= 90000, options: [
      { label: 'Buy it', run: () => { P.cash -= 90000; P.assets.push({ name: 'Haunted mansion', kind: 'home', value: 300000 }); unlock('homeowner'); if (chance(0.3)) { bump('happy', -8); return 'You bought it. Doors slam on their own at night. You try not to think about it.'; } bump('happy', 10); return 'You bought it. No ghosts, just a bargain.'; } },
      { label: 'Nope', run: () => 'You value your sleep.' },
    ] },
    { pack: 'drama', min: 18, max: 75, p: 0.03, text: () => "You're in a bank when it gets robbed.", options: [
      { label: 'Tackle the robber', run: () => (chance(0.45) ? (bump('happy', 15), P.cash += 10000, unlock('hero'), 'You stopped the robbery! The bank gave you a $10,000 reward.') : (bump('health', -25), 'You got hurt badly. You will think twice next time.')) },
      { label: 'Call the police quietly', run: () => (bump('happy', 4), 'The police caught them outside. You were a witness.') },
      { label: 'Hide', run: () => (bump('happy', -3), 'You hid under a desk until it was over.') },
    ] },
    { pack: 'drama', min: 20, max: 70, p: 0.05, when: () => !!partner(), text: () => `${partner().first}'s phone lights up with a message from someone saved as "❤️".`, options: [
      { label: 'Confront them', run: () => { const x = partner(); if (chance(0.5)) { x.bond = clamp(x.bond - 30); bump('happy', -12); return `${x.first} admitted to an affair.`; } x.bond = clamp(x.bond - 5); return `It was their mum. Saved as a heart. ${x.first} was hurt you asked.`; } },
      { label: 'Look through the phone', run: () => { const x = partner(); x.bond = clamp(x.bond - 15); return chance(0.4) ? (bump('happy', -10), `You found proof ${x.first} is cheating.`) : `Nothing there. But ${x.first} caught you snooping.`; } },
      { label: 'Let it go', run: () => 'You decided to trust them.' },
    ] },
    { pack: 'drama', min: 25, max: 70, p: 0.025, text: () => 'An eccentric billionaire offers you $1,000,000 to live alone on a remote island for a year.', options: [
      { label: 'Accept', run: () => { if (chance(0.75)) { P.cash += 1e6; bump('happy', 10); bump('health', -6); for (const x of P.people) if (x.alive) x.bond = clamp(x.bond - 15); return 'You lasted the year. You are a millionaire, a little sunburnt and very lonely.'; } bump('happy', -10); return 'You gave up after four months and got nothing.'; } },
      { label: 'Decline', run: () => 'You stayed with the people you love.' },
    ] },
    { pack: 'drama', min: 16, max: 60, p: 0.04, text: () => 'People keep mistaking you for a famous celebrity.', options: [
      { label: 'Play along', run: () => (chance(0.6) ? (bump('happy', 8), P.fame = (P.fame || 0) + 5, 'You signed autographs and got free dinners all year.') : (P.cash -= 2000, bump('happy', -6), 'The real celebrity\'s lawyers sent you a letter. That cost $2,000.')) },
      { label: 'Correct them', run: () => 'You patiently explained, again and again.' },
    ] },
    { pack: 'drama', min: 18, max: 85, p: 0.025, text: () => 'A stranger you once helped has left you their fortune in their will.', options: [
      { label: 'Claim it', run: () => { const w = rnd(4, 40) * 10000; P.cash += w; bump('happy', 10); return `After lawyer fees, you inherited ${money(w)}.`; } },
      { label: 'Donate it to charity', run: () => (bump('happy', 15), P.karma = (P.karma || 0) + 5, 'You gave it all away. A local paper wrote about you.') },
    ] },
    { pack: 'drama', min: 25, max: 75, p: 0.03, when: () => P.assets.some((a) => a.kind === 'car'), text: () => "After a minor fender bender, the other driver is suing you for $50,000.", options: [
      { label: 'Settle for $8,000', run: () => { P.cash -= 8000; return 'You settled. Annoying, but over.'; } },
      { label: 'Fight it in court', run: () => (chance(0.55) ? (bump('happy', 8), 'The jury laughed the case out of court.') : (P.cash -= 50000, bump('happy', -12), 'You lost. $50,000 gone.')) },
    ] },
    { pack: 'drama', min: 16, max: 40, p: 0.03, text: () => 'A band you love invites you to join their world tour as a roadie.', options: [
      { label: 'Join the tour', run: () => { if (P.job) { log(`You quit your job as ${jobTitle()}.`); P.job = null; } bump('happy', 15); bump('health', -5); return 'You toured 30 cities. Best year of your life.'; } },
      { label: 'Stay home', run: () => 'You watched the tour videos online.' },
    ] },
    { pack: 'drama', min: 30, max: 80, p: 0.015, text: () => 'A DNA kit reveals you were switched at birth.', options: [
      { label: 'Find your birth family', run: () => (bump('happy', chance(0.6) ? 10 : -10), chance(0.5) ? 'They welcomed you with open arms.' : 'They did not want to know you.') },
      { label: 'Keep it secret', run: () => (bump('happy', -3), 'You told no one. It weighs on you.') },
    ] },
  ],

  // ---------------------------------------------------------------- challenges (Challenge mode)
  challenges: [
    { id: 'mil40', icon: '💰', name: 'Millionaire by 40', desc: 'Reach a $1,000,000 net worth before you turn 40.',
      done: () => netWorth() >= 1e6, fail: () => P.age >= 40, progress: () => `${money(netWorth())} / $1,000,000 · ${Math.max(0, 40 - P.age)} yrs left` },
    { id: 'rags', icon: '🧹', name: 'Rags to riches', desc: 'Born into poverty. Reach a $5,000,000 net worth.', wealth: 0,
      done: () => netWorth() >= 5e6, progress: () => `${money(netWorth())} / $5,000,000` },
    { id: 'doctor', icon: '🩺', name: 'Doctor, doctor', desc: 'Become a doctor or surgeon.',
      done: () => !!P.job && P.job.career === 'doctor' && P.job.level >= 1, progress: () => (P.edu.medical ? 'Medical degree ✓ · get hired and promoted' : P.edu.degree ? "Bachelor's ✓ · get into medical school" : 'Get a degree first') },
    { id: 'family', icon: '👨‍👩‍👧‍👦', name: 'Big family', desc: 'Have 4 or more children.',
      done: () => kids().length >= 4, progress: () => `${kids().length} / 4 kids` },
    { id: 'century', icon: '🎂', name: 'Century', desc: 'Live to 100.',
      done: () => P.age >= 100, progress: () => `Age ${P.age} / 100` },
    { id: 'saint', icon: '😇', name: 'Model citizen', desc: 'Reach 60 with no criminal record and 10+ good deeds (volunteer).',
      done: () => P.age >= 60 && !P.record && (P.karma || 0) >= 10, fail: () => P.record > 0, progress: () => `Good deeds ${P.karma || 0} / 10 · record ${P.record ? '✗' : 'clean'}` },
  ],
};
