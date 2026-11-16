# 5 · Editing

Content Factory-ийн **Editing** станцыг нээхэд гишүүн харах зүйл. Хариуцагч: Editing manager.

---

## Энэ станц юу хийдэг вэ

Raw бичлэгийг Pinecone-ы reel болгоно. Та **reel-ийн төрлөө (theme) сонгоно**, таны Claude тэр
төрлийн засварын хэв маягаар (бүтэц, урт, хэмнэл, caption, карт, хөгжим, outro) бүгдийг хийнэ.
Theme бүрийг Pinecone-ы өөрийн 100 reel-ийн audit-аас (25 May - 5 Nov 2026) гаргасан, тиймээс гарах
видео account дээр байгаа reel-үүдтэй ижил харагдана.

## Reel-ийн төрлүүд (theme)

| Theme | Юу вэ | Audit median | Төлөв |
|---|---|---|---|
| Testimonial | Сурагч суугаад асуултад хариулна. Нэрийн гарчиг, асуултын карт | 13.5K | **Бэлэн** |
| PineQuest сэтгэгдэл | PineQuest-ийн оролцогч / шүүгчийн сэтгэгдэл. Hook гарчиг, багийн зураг, эффект, шинэ хөгжим | 1.6–17K | **Бэлэн** |
| Podcast clip | Podcast-аас 30–60 сек хэсэг, үг үгээр caption | 10.1K | **Бэлэн** |
| Motion teaser | Бичлэггүй, анимэйшнтэй зарлал (огноо, launch) | 9.1K | **Бэлэн** |
| Event recap | Эвент, хамтын ажиллагааны хурдан монтаж | 10.0K | Beta |
| Presenter promo | Ажилтан камер руу хөтөлбөр танилцуулна, list карт, CTA | 8.9K | Beta |
| Creator collab | Гаднын creator-ын vlog, бага засвар | **36.6K** | Beta |
| Office trend | Ажилтнууд trend хийнэ, утсаар бичсэн | 9.0K | Beta |
| Brand film | Жүжигчид + CGI кино | 12.8K | Зөвхөн төлөвлөгөө |

**Бэлэн** = батлагдсан хэв маягаар бүрэн автомат. **Beta** = Claude theme-ийн дүрмээр хийнэ, эхний
reel-үүд review-ээр батлагдсаны дараа Бэлэн болно. **Зөвхөн төлөвлөгөө** = зураг авалт эсвэл AI
generation хэрэгтэй, Claude shot list гаргана.

---

## Алхам алхмаар

### Нэг удаа тохируулах (~10 мин)

**1. Claude Code суулгах.** https://claude.com/claude-code (Mac, Windows, Linux).

**2. Chrome-д Claude extension суулгах** (Claude in Chrome). Transcript авахад хэрэгтэй.

**3. Editing skill-үүдийг суулгах.** Claude Code дотор:

```
/plugin marketplace add BavuuTheGreat/pinecone-editing-skills
/plugin install pinecone-video@pinecone-editing-skills
```

**4. Brand pack суулгах.** Фонт (GIP), Pinecone лого, end card нь нийтийн repo-д байхгүй. Editing manager-аас
`pinecone-brand-pack.zip` авна. Claude-д: `install the brand pack from ~/Downloads/pinecone-brand-pack.zip`.

**5. Тохиргоо хийлгэх.** Claude-д: `set up the editing station`. "Ready" гарвал бэлэн.

### Reel бүрт

**6. Бичлэгээ нэг folder-т хийх.**

**7. Claude-д хэлэх:** `edit a reel from ~/Downloads/<folder>`

**8. Theme сонгох.** Claude бичлэгийг үзээд тохирох theme-ийг санал болгоно (жишээ нь "Event recap:
тайз, үзэгчид, олон богино shot"). Та сонгоно. Шууд хэлж болно: `edit an event recap from …`

**9. Claude асуухад хариулах.** Тухайн theme-д хэрэгтэй зүйл: нэрс (зөв бичиглэлээр), эвент /
хөтөлбөрийн нэр, CTA, эргэлзээтэй үгс.

**10. Хүлээх.** Видео `~/Desktop/ai edited reels/` руу гарна (testimonial: `~/Desktop/ai captioned videos/`).

**11. Шалгах:**
- [ ] 1080×1920, хар зураасгүй
- [ ] Эхний 3 секундэд hook
- [ ] Нэр, caption зөв
- [ ] Өгүүлбэр бүр бүтэн дуусна
- [ ] Төгсгөлд Pinecone outro (trend-ээс бусад)

**12. Review-д оруулах.** Marketing Planner → Video review.

**13. Review comment ирвэл.** Screenshot өгөөд: `apply these reviewer comments to 03`

**14. Post хийхэд** хөгжмийн credit: `Music: "Funkorama" Kevin MacLeod (incompetech.com), CC BY 4.0`

---

## Бусад хэлж болох зүйл

| Хэлэх | Claude хийнэ |
|---|---|
| `show the reel themes` | Theme-үүдийг audit тоотой нь харуулна |
| `make testimonial reels from …` | Testimonial шууд |
| `make a PineQuest reel from <файл> — <нэр>, <баг> team, <байр>, team account @<handle>` | PineQuest сэтгэгдэл шууд |
| `clip the podcast …` | Podcast clip шууд |
| `refresh themes` (Editing manager) | Шинэ audit хийж theme-үүдийг шинэчилнэ |

## Одоохондоо гараар

- Mongolian transcript `dash.pinecone.mn/reel`-ээр browser дээр (API хараахан байхгүй).
- Нэрийн бичиглэлийг хүн шалгана.
- Beta theme-үүд review-ээр батлагдах хэрэгтэй.

Асуулт байвал: Editing manager.
