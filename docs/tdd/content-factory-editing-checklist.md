---
title: Content Factory — Editing автоматжуулахад хэрэгтэй зүйлс
category: checklist
authorIds: ['BavuuTheGreat']
status: DRAFT
---

Editing (5) бүрэн автомат ажиллахын тулд factory бүрээс хэрэгтэй зүйлс. ★ = эхлэхэд заавал хэрэгтэй.

## 4. Shooting manager

**Бичлэг бүрт (manifest):**

- [ ] ★ `video_id` (Scripting-ээс авсан)
- [ ] ★ Хүний нэр кирилл үсгээр, зөв бичгээр (жишээ нь Батбаяр уу, Батжав уу гэдэг эргэлзээ гарахгүй)
- [ ] ★ Format (testimonial, talking-head…) болон ашигласан асуултын жагсаалт, дарааллаар
- [ ] Тэмдэглэл: давтан бичсэн хэсэг, ашиглах take ("intro 2 дахь нь")

**Бичлэгийн дүрэм:**

- [ ] ★ Нэг хүн = нэг файл, нэр нь `video_id`-аар (`TST-2026-11-008.mp4`)
- [ ] ★ Сурагч болон ярилцлага авагч тусдаа микрофонтой, **тусдаа audio channel**-аар бичих (ярилцлага авагчийг 100% автоматаар хасах гол нөхцөл)
- [ ] ★ Нэг ижил тохиргоо: 4K босоо, 25fps, ижил гэрэл, ижил байрлал
- [ ] Асуулт дууссаны дараа 1 секунд хүлээгээд хариулах
- [ ] Сурагч эхэнд нэрээ тод хэлэх. Нэг асуултад нэг удаа, бүтэн өгүүлбэрээр хариулах
- [ ] Бичлэгийн эхэнд 5 секунд чимээгүй орчны дуу (room tone)
- [ ] ★ Нийтлэх зөвшөөрлийн (consent) бүртгэл хүн бүр дээр

**Хүргэлт:**

- [ ] ★ Нэг shared folder (Drive/NAS) руу raw + manifest-ийг хамт байршуулах. Pipeline тэр folder-ийг харж эхэлнэ

## 3. Scripting manager

- [ ] ★ Script бүрт `video_id`, format, асуултууд (дүрэм шалгасан, яг энэ үгээр)
- [ ] Видео бүрийн гол санаа, хүссэн урт, hook (эхний 3 секунд юу байх)
- [ ] Асуултын стандарт сан (testimonial-ийн 4 асуулт г.м.). Шинэ асуулт нэмбэл Editing-д мэдэгдэх

## 1–2. Messaging / Ideas manager

- [ ] Видео бүрийн зорилтот үзэгч, гол мессеж, CTA
- [ ] Ideas слот бүр ямар format-д хамаарахыг тэмдэглэх (Analytics format-аар харьцуулна)

## 6. Publishing manager

- [ ] ★ Editing-ээс юу хүлээж авахыг батлах: edited mp4, caption текст, attribution мөр, edit spec
- [ ] ★ Post хийсний дараа `video_id` ↔ post URL-ийг бүртгэх (Analytics-ийн холбоос үүнээс хамаарна)
- [ ] Instagram account-ийн API (Graph API) хандалт эсвэл зөвшөөрөл
- [ ] Боломжтой бол A/B: нэг ярилцлагын 2 хувилбарыг өөр өөр өдөр тавих

## 7. Analytics manager

- [ ] ★ Video бүрийн metric-ийг `video_id`-аар: views, 3s hold %, average watch %, retention curve, shares, saves, follows
- [ ] ★ Тогтмол хугацаанд татах: post-оос хойш 1, 7, 30 хоног
- [ ] Insight-ийг хэлбэржүүлэх: юуг өөрчлөх, ямар нотолгоогоор
- [ ] Зорилтот KPI (жишээ нь: average watch % ≥ 40)

## 5. Editing (надаас — Editing manager)

- [ ] ★ Review gate-ийг хэн, хэдэн цагт хийх (нэр, эргэлзээтэй caption)
- [ ] ★ Rulebook-ийг батлах: одоогийн дүрмүүд (hard cut, карт, хөгжим, caption style) албан ёсны болох
- [ ] Автомат өөрчлөлт хийх хязгаар (жишээ нь урт ±10%, hook сонголт). Түүнээс том нь таны зөвшөөрлөөр
- [ ] Албан ёсны brand assets: logo файл, фонтын лиценз (GIP), хөгжмийн лицензтэй сан

## Dev / IT

- [ ] ★ `dash.pinecone.mn/reel`-ийн transcript API (одоо browser-оор гараар авдаг)
- [ ] ★ Pipeline ажиллуулах server (Remotion render, ffmpeg) + байнгын хадгалах газар (одоо `/tmp`-д байгаа, устсан тохиолдол гарсан)
- [ ] Speechmatics custom vocabulary: "Pinecone" болон сурагчдын нэрс
- [ ] Content Factory app-д Editing station-ийн статус (Бичлэг хүлээж байна → Засварлаж байна → Батлах хүлээж байна → Дууссан)
- [ ] `video_id`-аар бүх factory-ийн өгөгдлийг холбох нэг storage (edit spec + metrics)
