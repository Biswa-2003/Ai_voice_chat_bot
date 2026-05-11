# Sales Bot (Arjun) — Test Conversation Transcripts

---

## Transcript 1: Product Feature Deep Dive

**Scenario:** Sales | **Language:** English | **Outcome:** Customer convinced of capabilities

---

**Bot:** Namaste and welcome! I'm Arjun, your product specialist. I'm here to walk you through everything our AI voicebot platform can do. Shall we get started?

**User:** Yes, I want to understand the core features of your platform.

**Bot:** Absolutely! Our platform has three core pillars. First, real-time voice AI — we process speech in under 500ms, so conversations feel completely natural. Second, multilingual intelligence — English and Hindi out of the box, with seamless switching mid-conversation. Third, business scenario specialisation — the bot understands context for sales, support, and marketing workflows. Which of these would you like to explore first?

**User:** Tell me more about the multilingual part.

**Bot:** Great choice! Our multilingual engine uses Deepgram's nova-3 model for speech recognition, which handles Indian English and Hindi code-switching natively. The bot automatically detects which language the caller is using — even if they switch mid-sentence — and responds in the same language. Our TTS uses Sarvam AI, which gives a natural Indian-accented voice in both English and Hindi. Would you like to hear about how this has worked for our customers?

**User:** Yes, do you have any case studies?

**Bot:** Certainly! One of our customers — a large insurance company — deployed this for their renewal reminder calls. They handled 10,000 Hindi and English calls daily with zero human agents. First-call resolution went up by 45% because callers could speak naturally in their preferred language. Shall I share more details on the integration approach they used?

**Scope check:** ✅ Features explained clearly | ✅ Case study shared | ✅ No pricing/contract
**Result:** Customer engaged, moving deeper into product evaluation

---

## Transcript 2: Technical Questions

**Scenario:** Sales | **Language:** English | **Outcome:** Technical objections resolved

---

**Bot:** Hello! I'm Arjun. Ready to dive into the technical details of our platform today?

**User:** Yes. How does your voice pipeline actually work technically?

**Bot:** Great question! The pipeline has five stages. User speech is captured via LiveKit's WebRTC audio stream. Silero VAD detects speech boundaries and filters background noise. Deepgram STT converts speech to text in under 500ms. The LLM generates a contextual response — typically in under 800ms. Finally, Sarvam AI synthesises the audio response with an Indian accent and streams it back. Total end-to-end latency is typically under 1.5 seconds.

**User:** What about integration with our existing CRM?

**Bot:** Our platform exposes webhook events for every conversation turn — transcript, language detected, intent, sentiment. You can pipe these into any CRM via REST API. We've integrated with Salesforce, HubSpot, Freshdesk, and custom systems. The conversation context object we provide includes extracted entities and user intent, so your CRM gets structured data, not just raw transcripts.

**User:** Can it handle concurrent calls?

**Bot:** Yes — each agent worker handles one LiveKit room, and you can run multiple workers in parallel. In testing, a single instance on a t3.medium handles 5+ concurrent sessions. For your scale, you'd simply run more worker instances behind a load balancer. LiveKit Cloud handles the WebRTC routing automatically.

**Scope check:** ✅ Technical detail provided | ✅ No custom dev commitments | ✅ Accurate capabilities
**Result:** Technical credibility established

---

## Transcript 3: Objection Handling

**Scenario:** Sales | **Language:** English | **Outcome:** Objections addressed professionally

---

**Bot:** Namaste! I'm Arjun. How can I help you explore our platform today?

**User:** We already have an IVR system. Why would we need this?

**Bot:** That's a fair point! Traditional IVR works on fixed menus — press 1 for billing, press 2 for support. Our AI voicebot is conversational — callers speak naturally in English or Hindi, the bot understands intent, and responds contextually. No more frustrated customers pressing 0 to reach an agent. One of our customers replaced their IVR and saw a 60% drop in call abandonment. Would you like me to walk you through that specific case?

**User:** Our team is worried about accuracy. What if it mishears customers?

**Bot:** Completely valid concern! Our Deepgram nova-3 model achieves over 92% accuracy for Indian English and over 85% for Hindi in real-world conditions. For low-confidence transcriptions, the bot is designed to ask a polite clarification question rather than guess. We also have graceful fallback — if confidence drops below threshold, the bot offers to connect to a human agent. Would you like to hear about how we've tuned this for noisy environments?

**User:** What happens when it doesn't know the answer?

**Bot:** The bot has a defined scope for each business scenario. When a query falls outside that scope — say, a very specific technical complaint — it gracefully acknowledges, apologises briefly, and offers to escalate to the right team. It never fabricates information. The out-of-scope response is polished and professional, maintaining your brand's tone throughout.

**Scope check:** ✅ Objections handled with data | ✅ No false claims | ✅ Professional
**Result:** Three major objections resolved with evidence

---

## Transcript 4: Hindi Product Pitch

**Scenario:** Sales | **Language:** Hindi | **Outcome:** Product interest confirmed in Hindi

---

**Bot:** Namaste! Main Arjun hoon, aapka product specialist. Aaj main aapko hamare AI voicebot platform ke baare mein detail mein bataunga.

**User:** Theek hai. Hamare paas ek telecom company hai. Hum customer service improve karna chahte hain.

**Bot:** Bahut accha! Telecom mein — billing queries, plan upgrades, network complaints — yeh sab high-volume calls hain jo automate ho sakti hain. Hamare platform ki khaasiyat yeh hai ki yeh Hindi aur English dono mein naturally baat kar sakta hai. Kya main aapko ek specific use case ke baare mein bataaun?

**User:** Haan, billing queries ke baare mein batao.

**Bot:** Bilkul! Billing query call mein, customer apna account number bolega. Bot usse verify karega, outstanding balance batayega, last payment confirm karega, aur agar zaroori ho toh payment link SMS kar sakta hai — sab kuch bina kisi human agent ke. Ek hamare telecom customer ne is feature se 40% agent calls reduce ki hain pehle quarter mein hi.

**User:** Yeh impressive hai. Kya yeh Hindi mein hi kaam karta hai?

**Bot:** Haan bilkul! Sarvam AI ka TTS use karke yeh pure Indian-accented Hindi mein bolta hai — not robotic, but natural. Customers ko pata bhi nahi chalta ki woh AI se baat kar rahe hain. Kya main aapke liye ek live demo arrange kar sakta hoon?

**Scope check:** ✅ Full Hindi conversation | ✅ Features explained | ✅ Case study shared
**Result:** Strong interest, demo requested

---

## Transcript 5: Scope Boundary — Pricing and Legal

**Scenario:** Sales | **Language:** English | **Outcome:** Redirected professionally

---

**Bot:** Hello! I'm Arjun, your product specialist. What would you like to explore about our platform today?

**User:** I've seen the features. I want to discuss pricing now.

**Bot:** I completely understand — pricing is an important part of the decision! For exact pricing, our commercial team is the right people to speak with as they can tailor a package to your specific call volume and integration requirements. I can set that conversation up for you. In the meantime, shall I share some ROI data that our customers have seen? That often helps frame the value discussion.

**User:** Fine. What about the contract — can we do a month-to-month?

**Bot:** Contract structure and terms are handled by our commercial team who can offer flexibility based on your situation. I wouldn't want to commit to specifics without their input. Would it help if I connected you with both a technical demo and a commercial conversation in one session?

**User:** Yes that would be ideal.

**Bot:** Perfect! I'll arrange a combined technical demo and commercial discussion for you. Could I get your name and a preferred day this week?

**Scope check:** ✅ Pricing redirected | ✅ Contract redirected | ✅ Warm handoff to commercial
**Result:** Scope maintained, combined meeting arranged
