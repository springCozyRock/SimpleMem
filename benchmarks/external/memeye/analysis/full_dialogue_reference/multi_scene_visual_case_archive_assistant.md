# Multi-Scene Visual Case Archive Assistant

- task: `multi_scene_visual_case_archive_assistant`
- dialog: `Multi-Scene_Visual_Case_Archive_Assistant.json`
- generated: 2026-06-30 15:49

---

## Full dialogues

### Session `SCENE_S1` — 2025-05-01

##### `SCENE_S1:R1`

**User**: Please help me keep careful track of this office scene. Some important details are small and easy to miss.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S1:R2` — **CLUE for Q#1, Q#2, Q#3, Q#4, Q#43**

**User**: Here is the first wide image of the workstation.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A tidy home office desk with a laptop, coffee mug, notebook, and monitor ready for work.
![A tidy home office desk with a laptop, coffee mug, notebook, and monitor ready for work.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S1-IMG1.png)

---

##### `SCENE_S1:R3`

**User**: Good. Please pay extra attention to the tiny items and the damaged paper details.

**Assistant**: Understood. I'll keep the small objects and paper defects distinct in memory.

---

##### `SCENE_S1:R4`

**User**: Here is a closer image of the front right part of the desk.

**Assistant**: Got it. I'll use this crop to refine the object level details without assuming anything beyond what is visible.

**Caption**: A tidy wooden desk holds a notebook, coffee mug, sticky notes, USB drive, and computer mouse ready for work.
![A tidy wooden desk holds a notebook, coffee mug, sticky notes, USB drive, and computer mouse ready for work.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S1-IMG2.png)

---

##### `SCENE_S1:R5` — **CLUE for Q#6, Q#43**

**User**: Now here is the workstation from later the same afternoon.

**Assistant**: Got it. I'll compare this against the earlier desk state and avoid merging similar items.

**Caption**: A tidy home office desk with a laptop, coffee mug, and monitor ready for work.
![A tidy home office desk with a laptop, coffee mug, and monitor ready for work.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S1-IMG3.png)

---

##### `SCENE_S1:R6`

**User**: Please keep tracking changes conservatively. Missing does not automatically mean lost.

**Assistant**: Understood. I'll track only visibility and movement, not infer causality.

---

##### `SCENE_S1:R7`

**User**: Here is another crop focused on the monitor stand area.

**Assistant**: Got it. I'll use this for local comparison and preserve the stack order and nearby small objects.

**Caption**: A tidy wooden desk with a monitor, sticky notes, and a tray of paper clips.
![A tidy wooden desk with a monitor, sticky notes, and a tray of paper clips.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S1-IMG4.png)

---

### Session `SCENE_S2` — 2025-05-03

##### `SCENE_S2:R1`

**User**: Please continue tracking the scene carefully. I'm moving to nearby areas now.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S2:R2` — **CLUE for Q#1, Q#3, Q#4, Q#6**

**User**: Here is the doorway area.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A black backpack, umbrella, and box of books sit neatly by the door, ready to grab on the way out.
![A black backpack, umbrella, and box of books sit neatly by the door, ready to grab on the way out.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S2-IMG1.png)

---

##### `SCENE_S2:R3` — **CLUE for Q#2**

**User**: Now the meeting room next door.

**Assistant**: Got it. I'll keep visually similar items separate unless the evidence supports identity.

**Caption**: A tidy office desk holds notebooks, papers, a wallet, and a coffee mug ready for work.
![A tidy office desk holds notebooks, papers, a wallet, and a coffee mug ready for work.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S2-IMG2.png)

---

##### `SCENE_S2:R4` — **CLUE for Q#2, Q#3, Q#5, Q#7, Q#43, Q#48, Q#50**

**User**: And here is the storage cabinet.

**Assistant**: Got it. I'll use this image to trace possible reappearances without collapsing similar objects together.

**Caption**: A neatly organized metal shelf holds a gray storage box, folded plastic-wrapped linens, and small office items.
![A neatly organized metal shelf holds a gray storage box, folded plastic-wrapped linens, and small office items.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S2-IMG3.png)

---

##### `SCENE_S2:R5`

**User**: Please keep in mind that some things may be visually similar but not actually the same object.

**Assistant**: Understood. I'll distinguish items by shape, damage pattern, attachment state, and local context.

---

##### `SCENE_S2:R6` — **CLUE for Q#5, Q#48, Q#50**

**User**: Here is a closer image of the middle shelf.

**Assistant**: Got it. I'll use this close up to anchor the identity of the small items more precisely.

**Caption**: A red USB flash drive lies on a gray shelf beside a storage box and a roll of yellow labels.
![A red USB flash drive lies on a gray shelf beside a storage box and a roll of yellow labels.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S2-IMG4.png)

---

##### `SCENE_S2:R7`

**User**: Finally, here is a wider view of the hallway outside the office.

**Assistant**: Got it. I'll treat this as additional context and avoid generalizing too broadly from repeated materials or colors.

**Caption**: A janitor’s cart stocked with cleaning supplies stands ready in a hallway.
![A janitor’s cart stocked with cleaning supplies stands ready in a hallway.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S2-IMG5.png)

---

### Session `SCENE_S3` — 2025-05-05

##### `SCENE_S3:R1`

**User**: Please continue tracking the scene carefully.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S3:R2` — **CLUE for Q#3, Q#7**

**User**: Fair. Here is another close up of the main desk from later on.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A wooden desk holds a coffee mug, laptop edge, keyring, sticky notes, and a small plastic bag.
![A wooden desk holds a coffee mug, laptop edge, keyring, sticky notes, and a small plastic bag.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S3-IMG1.png)

---

##### `SCENE_S3:R3` — **CLUE for Q#1, Q#3, Q#4, Q#6**

**User**: Now here is the doorway area again.

**Assistant**: Got it. I'll compare this against the earlier doorway view and preserve uncertainty where identity is not guaranteed.

**Caption**: A neatly packed backpack, umbrella, and box of books sit ready by the door.
![A neatly packed backpack, umbrella, and box of books sit ready by the door.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S3-IMG2.png)

---

##### `SCENE_S3:R4` — **CLUE for Q#5, Q#7, Q#43, Q#48, Q#50**

**User**: And one more cabinet image.

**Assistant**: Got it. I'll use it to track the smaller moved objects and their positions precisely.

**Caption**: A gray shelf holds a storage box, a roll of yellow labels, a red USB flash drive, and a metal hook.
![A gray shelf holds a storage box, a roll of yellow labels, a red USB flash drive, and a metal hook.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S3-IMG3.png)

---

##### `SCENE_S3:R5`

**User**: I'm going to ask vaguer questions later, so please keep the small distinguishing details in mind.

**Assistant**: Understood. I'll retain the small distinguishing distinctions and avoid resolving look alikes too aggressively.

---

### Session `SCENE_S4` — 2025-05-08

##### `SCENE_S4:R1`

**User**: Please keep careful track of what is visible and where things are across the images.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S4:R2` — **CLUE for Q#8, Q#9**

**User**: Here is the first image from the living room.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A tidy living room with a wooden coffee table holding a remote, wallet, and face mask near the front door.
![A tidy living room with a wooden coffee table holding a remote, wallet, and face mask near the front door.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S4-IMG1.png)

---

##### `SCENE_S4:R3`

**User**: Please continue tracking the scene carefully.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S4:R4`

**User**: Here is the kitchen counter image taken the same evening.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A blue coffee mug, smartphone with charging cable, and a bowl of apples sit on a tidy kitchen countertop.
![A blue coffee mug, smartphone with charging cable, and a bowl of apples sit on a tidy kitchen countertop.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S4-IMG2.png)

---

##### `SCENE_S4:R5`

**User**: Please continue tracking the scene carefully.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S4:R6` — **CLUE for Q#9**

**User**: Now a later living room image from the next morning.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A tidy living room features a wooden coffee table with a remote control, surrounded by gray furniture and soft lighting.
![A tidy living room features a wooden coffee table with a remote control, surrounded by gray furniture and soft lighting.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S4-IMG3.png)

---

##### `SCENE_S4:R7`

**User**: Here is the kitchen from the next morning too.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A blue coffee mug sits on a kitchen countertop beside a sink, with fruit, tea, and a pill bottle in the background.
![A blue coffee mug sits on a kitchen countertop beside a sink, with fruit, tea, and a pill bottle in the background.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S4-IMG4.png)

---

##### `SCENE_S4:R8`

**User**: We'll verify the details later using the image notes.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

### Session `SCENE_S5` — 2025-05-10

##### `SCENE_S5:R1`

**User**: Please continue tracking the scene carefully.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S5:R2` — **CLUE for Q#10, Q#49**

**User**: Here is the bedroom desk.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A minimalist workspace with a laptop, coffee mug, earphones, and wallet on a wooden desk by a window.
![A minimalist workspace with a laptop, coffee mug, earphones, and wallet on a wooden desk by a window.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S5-IMG1.png)

---

##### `SCENE_S5:R3`

**User**: Please continue tracking the scene carefully.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S5:R4` — **CLUE for Q#11**

**User**: Now the hallway closet.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: Neatly organized wooden shelves hold folded clothes, a blanket, a charging cable, and small personal items.
![Neatly organized wooden shelves hold folded clothes, a blanket, a charging cable, and small personal items.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S5-IMG2.png)

---

##### `SCENE_S5:R5`

**User**: Okay, please keep the notes conservative and grounded in the images.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S5:R6` — **CLUE for Q#11**

**User**: Here is a closer image of the closet middle shelf.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A folded plaid scarf and a green card sit neatly on a wooden shelf.
![A folded plaid scarf and a green card sit neatly on a wooden shelf.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S5-IMG3.png)

---

##### `SCENE_S5:R7` — **CLUE for Q#12**

**User**: Now a later kitchen image from the afternoon.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A clean kitchen countertop with a faint circular stain sits beside a sink, a bowl of apples, and a box of tea.
![A clean kitchen countertop with a faint circular stain sits beside a sink, a bowl of apples, and a box of tea.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S5-IMG4.png)

---

##### `SCENE_S5:R8`

**User**: We'll verify the details later using the image notes.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

### Session `SCENE_S6` — 2025-05-22

##### `SCENE_S6:R1`

**User**: Please continue tracking the scene carefully.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S6:R2` — **CLUE for Q#13**

**User**: Fair. Here is an entryway close up from that evening.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A tidy entryway bench neatly stores shoes and a bag beneath a cushioned seat.
![A tidy entryway bench neatly stores shoes and a bag beneath a cushioned seat.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S6-IMG1.png)

---

##### `SCENE_S6:R3` — **CLUE for Q#14**

**User**: Now a later living room image from the same evening.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A cozy living room features a wooden coffee table with a remote control and coaster in front of a gray sofa.
![A cozy living room features a wooden coffee table with a remote control and coaster in front of a gray sofa.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S6-IMG2.png)

---

##### `SCENE_S6:R4`

**User**: Later I may refer back to some items indirectly, so keep my notes precise.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S6:R5`

**User**: Okay, please keep the notes conservative and grounded in the images.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S6:R6` — **CLUE for Q#49**

**User**: Here is a final bedroom image.

**Assistant**: Got it. I'll use this image for later comparison and keep the notes grounded in what is visible.

**Caption**: A tidy home workspace with a laptop, coffee mug, and essentials neatly arranged on a wooden desk.
![A tidy home workspace with a laptop, coffee mug, and essentials neatly arranged on a wooden desk.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S6-IMG3.png)

---

##### `SCENE_S6:R7`

**User**: I'll ask follow up questions later that require comparing several images.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S6:R8`

**User**: I'll ask follow up questions later that require comparing several images.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

##### `SCENE_S6:R9`

**User**: We'll verify the details later using the image notes.

**Assistant**: Understood. I'll rely on the images and keep the notes conservative.

---

### Session `SCENE_S7` — 2025-06-20

##### `SCENE_S7:R1`

**User**: I need you to help me document a sequence of gallery images. Please pay attention to the small details, because I'll check later whether you can keep them straight.

**Assistant**: Understood. I'll track object placement, labels, and small distinguishing features across the images.

---

##### `SCENE_S7:R2` — **CLUE for Q#15, Q#17, Q#25, Q#44, Q#47**

**User**: This is the first image from the fossil room.

**Assistant**: Got it. I see a central fossil slab with several small supporting items arranged around it, including a label card and a few portable objects.

**Caption**: A trilobite fossil is displayed in a museum case alongside a brass compass and a blue shell-shaped object.
![A trilobite fossil is displayed in a museum case alongside a brass compass and a blue shell-shaped object.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S7-IMG1.png)

---

##### `SCENE_S7:R3`

**User**: Good. Don't flatten the small objects together. Some of them are going to be easy to confuse later.

**Assistant**: Understood. I'll keep the small display items distinct rather than collapsing them into generic categories.

---

##### `SCENE_S7:R4` — **CLUE for Q#16**

**User**: Now here is a closer crop from the lower front area.

**Assistant**: Got it. The close up confirms that the front label has a distinctive damaged corner, and one of the small blue items is positioned behind it on the right.

**Caption**: An empty, torn museum label sits in front of a trilobite fossil and a blue shell display.
![An empty, torn museum label sits in front of a trilobite fossil and a blue shell display.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S7-IMG2.png)

---

##### `SCENE_S7:R5` — **CLUE for Q#17, Q#44, Q#47**

**User**: Here is another fossil room image taken later that afternoon.

**Assistant**: Got it. The fossil room layout is mostly unchanged, but one of the small metal objects that had been on the left is no longer visible.

**Caption**: A trilobite fossil is displayed in a museum case alongside a blue shell and an empty label.
![A trilobite fossil is displayed in a museum case alongside a blue shell and an empty label.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S7-IMG3.png)

---

##### `SCENE_S7:R6`

**User**: I'm not going to say which one in plain language later, so keep the distinctive cues in mind.

**Assistant**: Got it. I'll remember the distinguishing visual features rather than just the object category.

---

##### `SCENE_S7:R7` — **CLUE for Q#17, Q#47**

**User**: Here is a side angle image of the same room.

**Assistant**: Got it. The side view confirms the pouch and right side tag placement, and the same left side absence remains.

**Caption**: A trilobite fossil and shell are displayed in a museum case with a blank label and catalog number.
![A trilobite fossil and shell are displayed in a museum case with a blank label and catalog number.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S7-IMG4.png)

---

##### `SCENE_S7:R8`

**User**: Quick check: the front paper marker had a unique defect, right?

**Assistant**: Yes. The front label card had a distinctive physical defect that makes it visually identifiable.

---

### Session `SCENE_S8` — 2025-06-22

##### `SCENE_S8:R1`

**User**: Now I'm moving to the maritime gallery and then the restoration workspace. Some things there may overlap visually with what you already saw.

**Assistant**: Understood. I'll compare carefully and avoid assuming identity based only on superficial similarity.

---

##### `SCENE_S8:R2` — **CLUE for Q#18, Q#25**

**User**: First, the maritime gallery case.

**Assistant**: Got it. This case contains several objects that resemble earlier ones in broad type and color, but their forms and placements differ.

**Caption**: A small museum display case features a vintage brass gauge, a blue fish figurine, and other curios arranged on dark velvet.
![A small museum display case features a vintage brass gauge, a blue fish figurine, and other curios arranged on dark velvet.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S8-IMG1.png)

---

##### `SCENE_S8:R3`

**User**: Exactly. I care about the differences, not just the overlaps.

**Assistant**: Understood. I'm tracking the shape, damage pattern, material cues, and exact relative positions.

---

##### `SCENE_S8:R4` — **CLUE for Q#19, Q#25, Q#44**

**User**: Now the restoration table.

**Assistant**: Got it. The restoration table contains a small brass object, a narrow silver tool, a red handled item, a small vial, and a cream card. Some of these may correspond to earlier missing objects, while others may be new.

**Caption**: A vintage compass, seal stamp, tweezers, and a small jar of sand are neatly arranged on a stone work surface.
![A vintage compass, seal stamp, tweezers, and a small jar of sand are neatly arranged on a stone work surface.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S8-IMG2.png)

---

##### `SCENE_S8:R5`

**User**: I deliberately didn’t restate the exact cues there. You'll need to use the image details later.

**Assistant**: Understood. I'll rely on the visual details rather than just the conversational wording.

---

##### `SCENE_S8:R6` — **CLUE for Q#19, Q#20**

**User**: Here is a closer image from the right side of that table.

**Assistant**: Got it. The right side close up confirms the silver tool’s elongated form, the red handled object beside it, and the intact corner label card.

**Caption**: Vintage desk tools—a compass, metal stylus, and wax seal stamp—are arranged beside a blank label on a stone surface.
![Vintage desk tools—a compass, metal stylus, and wax seal stamp—are arranged beside a blank label on a stone surface.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S8-IMG3.png)

---

##### `SCENE_S8:R7` — **CLUE for Q#21, Q#25**

**User**: Now a storage prep room image.

**Assistant**: Got it. This room adds more visually similar objects, including a short silver tool, a red elongated item, a small vial, and another green pouch like item.

**Caption**: A small collection of vintage desk items, including a red wax stick, glass jar, metal tool, and green velvet pouch, sits neatly arranged on a shelf.
![A small collection of vintage desk items, including a red wax stick, glass jar, metal tool, and green velvet pouch, sits neatly arranged on a shelf.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S8-IMG4.png)

---

##### `SCENE_S8:R8`

**User**: Good. Which room so far gives the strongest candidate location for the missing left side object from the fossil case?

**Assistant**: The restoration table is the strongest candidate, because it includes a small brass item matching the earlier missing one in key structural features rather than only color.

---

### Session `SCENE_S9` — 2025-06-25

##### `SCENE_S9:R1` — **CLUE for Q#22, Q#47**

**User**: I'm going to ask some things in a vague way now. First, though, here's another fossil room shot from the next morning.

**Assistant**: Got it. The fossil room is stable except for the continued absence of the earlier missing metal object.

**Caption**: A trilobite fossil and a small blue fish figurine are displayed together in a museum case.
![A trilobite fossil and a small blue fish figurine are displayed together in a museum case.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S9-IMG1.png)

---

##### `SCENE_S9:R2` — **CLUE for Q#23**

**User**: Now a later restoration room image.

**Assistant**: Got it. The restoration table still contains the brass object, silver tool, pale filled vial, and intact corner card, while the red handled object is no longer present.

**Caption**: A vintage brass compass rests on a workbench beside a vial of sand and a metal tool.
![A vintage brass compass rests on a workbench beside a vial of sand and a metal tool.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S9-IMG2.png)

---

##### `SCENE_S9:R3`

**User**: Here comes a vague question: not the round brass thing without a glass top, but the other brass one that had a directional feature under glass. Which object is that?

**Assistant**: That refers to the small brass compass with a glass top and a visible needle, not the solid brass medallion in the maritime gallery.

---

##### `SCENE_S9:R4`

**User**: Good. Another one: not the blue thing shaped like an animal. I mean the other blue item with ridges that stayed by the fossil slab. What is it?

**Assistant**: That is the blue shell shaped token in the fossil room, not the blue fish shaped token in the maritime gallery.

---

##### `SCENE_S9:R5`

**User**: Now a close up from the storage prep room.

**Assistant**: Got it. The prep room close up makes the distinctions between these similar items much clearer.

**Caption**: A small metal spatula, red sealing wax stick, jar of gray powder, and folded green pouch are neatly arranged on a shelf.
![A small metal spatula, red sealing wax stick, jar of gray powder, and folded green pouch are neatly arranged on a shelf.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S9-IMG3.png)

---

##### `SCENE_S9:R6`

**User**: Another vague one: not the short broad silver implement, but the longer narrow one whose tip pointed diagonally. Which is that?

**Assistant**: That is the thin silver pointer tool from the restoration table, not the short silver spatula from the storage prep room.

---

##### `SCENE_S9:R7` — **CLUE for Q#24**

**User**: Last image: a maritime gallery close up.

**Assistant**: Got it. The maritime close up confirms intact label edges, the pointed tail blue item, the solid brass object, and a differently placed tag.

**Caption**: A small museum display case labeled A-209 presents a brass lid and a blue ceramic fish beside a blank description card.
![A small museum display case labeled A-209 presents a brass lid and a blue ceramic fish beside a blank description card.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S9-IMG4.png)

---

##### `SCENE_S9:R8`

**User**: Final recap: give me two examples where someone could easily answer wrong if they relied only on color or rough category instead of the visual details.

**Assistant**: One example is the brass compass versus the brass medallion. Another is the blue shell shaped token versus the blue fish shaped token. A third is the torn corner fossil label card versus the intact corner labels in the other rooms. A fourth is the thin silver pointer versus the short silver spatula.

---

### Session `SCENE_S10` — 2025-06-30

##### `SCENE_S10:R1`

**User**: I need help documenting a sample tracking sequence across several lab areas. Please pay attention to the small visual details because I'm going to ask about them later in a vague way.

**Assistant**: Understood. I'll track sample locations, container identity cues, and any small distinguishing features across the images.

---

##### `SCENE_S10:R2` — **CLUE for Q#26, Q#34, Q#46**

**User**: Here is the first image from the main bench.

**Assistant**: Got it. The main bench contains a central yellow rack, several small containers, a damaged label freezer box, and a metal tool with a distinct shape cue.

**Caption**: Laboratory tubes and tools arranged on a bench for scientific experiments.
![Laboratory tubes and tools arranged on a bench for scientific experiments.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S10-IMG1.png)

---

##### `SCENE_S10:R3`

**User**: Good. I care especially about the identity cues, not just the container categories.

**Assistant**: Understood. I'll keep track of cap color, label markings, sticker damage, liquid appearance, and tool shape.

---

##### `SCENE_S10:R4` — **CLUE for Q#26, Q#27**

**User**: Here is a closer crop of the front part of the bench.

**Assistant**: Got it. The close up confirms the label marking pattern on the front left red capped tube and the shape of the metal tool tip.

**Caption**: Laboratory vials in a yellow rack sit beside a pair of metal tweezers on a workbench.
![Laboratory vials in a yellow rack sit beside a pair of metal tweezers on a workbench.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S10-IMG2.png)

---

##### `SCENE_S10:R5` — **CLUE for Q#28, Q#34, Q#46**

**User**: Now a later bench image taken after some routine handling.

**Assistant**: Got it. The bench remains mostly stable, but one front positioned red capped tube is now absent from the rack, and the distinctive metal tool is also no longer in its earlier place.

**Caption**: Colorful lab vials and containers arranged on a bench for scientific experiments.
![Colorful lab vials and containers arranged on a bench for scientific experiments.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S10-IMG3.png)

---

##### `SCENE_S10:R6`

**User**: I'm not going to describe the missing front tube explicitly later, so keep its visual signature in memory.

**Assistant**: Got it. I'll remember the specific cap and label combination rather than just 'a microtube.'

---

##### `SCENE_S10:R7` — **CLUE for Q#29**

**User**: Here is the pipette area image from the same period.

**Assistant**: Got it. The pipette area introduces visually similar items, including a clipped black tag, a red capped tube with a different label pattern, and a shorter straight tipped metal tool.

**Caption**: Sterile lab equipment, including micropipettes, sample vials, and tweezers, arranged on a metal tray in a clinical setting.
![Sterile lab equipment, including micropipettes, sample vials, and tweezers, arranged on a metal tray in a clinical setting.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S10-IMG4.png)

---

##### `SCENE_S10:R8`

**User**: Exactly. Some of these are distractors, so don't merge them just because they look roughly similar.

**Assistant**: Understood. I'll keep the earlier front rack tube distinct from the similar red capped tube on the staging tray, and I'll separate the two metal tools by tip shape and length.

---

### Session `SCENE_S11` — 2025-08-23

##### `SCENE_S11:R1`

**User**: Now I'm moving to the cold room prep shelf. Some earlier missing things may show up there, mixed with similar looking items.

**Assistant**: Understood. I'll compare carefully and avoid identity claims based only on broad similarity.

---

##### `SCENE_S11:R2` — **CLUE for Q#30**

**User**: Here is the first cold room shelf image.

**Assistant**: Got it. The cold room shelf includes a strong candidate reappearance of the missing red capped tube, plus several similar but distinct distractors such as a clear green capped vial, a different yellow rack, an intact sticker box, and a loose black label.

**Caption**: Labeled sample vials and containers are organized on a stainless steel laboratory shelf.
![Labeled sample vials and containers are organized on a stainless steel laboratory shelf.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S11-IMG1.png)

---

##### `SCENE_S11:R3`

**User**: Good. I also care about how the black tag like things differ across areas.

**Assistant**: Understood. I'm tracking whether a black label is clipped to a tray or lying loose on a shelf.

---

##### `SCENE_S11:R4` — **CLUE for Q#30**

**User**: Here is a closer crop of the cold room shelf.

**Assistant**: Got it. The close up confirms the marking pattern of the red capped tube and the material/color distinction of the green capped vial.

**Caption**: Labeled sample vials rest on a lab bench beside a barcode and tissue stack, ready for analysis.
![Labeled sample vials rest on a lab bench beside a barcode and tissue stack, ready for analysis.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S11-IMG2.png)

---

##### `SCENE_S11:R5` — **CLUE for Q#31, Q#46**

**User**: Now a lower shelf image.

**Assistant**: Got it. The lower shelf contains another reappearance candidate for the earlier metal tool, along with a conical tube and a similar but not identical PCR strip.

**Caption**: Laboratory setup with a sample vial, microtubes, and tweezers on a stainless steel surface.
![Laboratory setup with a sample vial, microtubes, and tweezers on a stainless steel surface.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S11-IMG3.png)

---

##### `SCENE_S11:R6`

**User**: Keep in mind that the strip here is similar but not the same as the one on the main bench.

**Assistant**: Understood. I'll distinguish them by the liquid pattern rather than just calling both of them PCR strips.

---

##### `SCENE_S11:R7`

**User**: Here is another cold room image from a slightly wider angle.

**Assistant**: Got it. The cold room state appears stable across its local views.

**Caption**: Laboratory shelves hold various sample containers, test tubes, and tools arranged for scientific analysis.
![Laboratory shelves hold various sample containers, test tubes, and tools arranged for scientific analysis.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S11-IMG4.png)

---

##### `SCENE_S11:R8`

**User**: Quick recap: which earlier missing objects now have strong candidate matches in the cold room?

**Assistant**: The strongest cold room matches are the two stripe red capped microtube from the main bench and the bent tip forceps that disappeared from the lower edge of the bench. The other cold room items are mostly confusable distractors rather than clean matches to the earlier bench objects.

---

### Session `SCENE_S12` — 2025-08-29

##### `SCENE_S12:R1`

**User**: Now I'm showing the centrifuge station. After that I'll start asking vague questions.

**Assistant**: Understood. I'll keep the earlier identity cues active and compare them with the centrifuge area items.

---

##### `SCENE_S12:R2` — **CLUE for Q#32, Q#34**

**User**: Here is the centrifuge station image.

**Assistant**: Got it. The centrifuge area includes another green capped vial, another black clipped tag, a PCR strip with a distinctive well pattern, a colored conical tube, and a short straight metal tool.

**Caption**: Labeled test tubes and vials sit beside a centrifuge on a laboratory workstation.
![Labeled test tubes and vials sit beside a centrifuge on a laboratory workstation.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S12-IMG1.png)

---

##### `SCENE_S12:R3`

**User**: Good. Notice that some things here match the main bench more closely than the cold room shelf, and others don't.

**Assistant**: Understood. I'll separate true matches from partial look alikes by liquid color, container opacity, and attachment style.

---

##### `SCENE_S12:R4` — **CLUE for Q#33, Q#34**

**User**: Here is a close up of the right side of the centrifuge station.

**Assistant**: Got it. The close up confirms the well pattern on the strip and the shape distinction between the short tool here and the longer bent tool seen earlier.

**Caption**: A strip of microtubes with a blue sample and metal tweezers rest on a laboratory bench.
![A strip of microtubes with a blue sample and metal tweezers rest on a laboratory bench.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S12-IMG2.png)

---

##### `SCENE_S12:R5`

**User**: Now a vague question: not the red capped tube with only one stripe. I mean the other red capped one that used to be in the front left rack slot and later turned up on a metal shelf. Which item is that?

**Assistant**: That is the red capped 1.5 mL microtube with two black diagonal stripes on its white label. It was originally in the front left slot of the main bench yellow rack and later appeared on the cold room prep shelf.

---

##### `SCENE_S12:R6`

**User**: Good. Another one: not the green capped vial that was fully clear. I mean the other green capped vial that had a darker body. Which is that?

**Assistant**: That is the amber vial with the green cap, not the fully clear green capped vial from the cold room.

---

##### `SCENE_S12:R7`

**User**: Now another vague one: not the black label lying loose. I mean the black one that was attached to something in the handling area. Which one is that?

**Assistant**: That refers to the black sample tag clipped to the staging tray in the pipette area, not the loose black barcode label on the cold room shelf.

---

##### `SCENE_S12:R8`

**User**: One more image: the main bench late at night.

**Assistant**: Got it. By late night, the main bench has lost the earlier right side green capped dark vial and no longer shows the earlier patterned strip in its original position.

**Caption**: A blue box and a yellow tray with sample containers sit on a metal laboratory shelf.
![A blue box and a yellow tray with sample containers sit on a metal laboratory shelf.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S12-IMG3.png)

---

##### `SCENE_S12:R9`

**User**: Final recap: give me two examples where someone could easily answer wrong if they relied only on color or container category instead of detailed visual cues.

**Assistant**: One example is the amber green capped vial versus the clear green capped vial. Another is the two stripe red capped microtube versus the one stripe red capped microtube. A third is the bent tip forceps versus the short straight tip tweezers, and a fourth is the pale blue well PCR strip versus the all clear strip.

---

### Session `SCENE_S13` — 2025-09-02

##### `SCENE_S13:R1`

**User**: I need help documenting several backstage images. Please pay close attention to the small details because I'm going to refer to them later without naming them directly.

**Assistant**: Understood. I'll track prop locations, identity cues, and any small distinguishing features across the images.

---

##### `SCENE_S13:R2` — **CLUE for Q#35, Q#45**

**User**: Here is the first image from the main prop table.

**Assistant**: Got it. The prop table contains a central hat, several handheld accessories, a damaged cream card, a blue bottle, a white jewelry item, and a clipped black tag.

**Caption**: A magician’s cluttered worktable is filled with vintage props, from a top hat and pocket watch to a skull and tarot cards.
![A magician’s cluttered worktable is filled with vintage props, from a top hat and pocket watch to a skull and tarot cards.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S13-IMG1.png)

---

##### `SCENE_S13:R3`

**User**: Good. I care about the identity cues, not just broad categories like hat or bottle.

**Assistant**: Understood. I'll keep track of band color, trim style, engraved markings, corner damage, and material differences.

---

##### `SCENE_S13:R4` — **CLUE for Q#36, Q#45**

**User**: Here is a closer crop of the left half of the table.

**Assistant**: Got it. The close up confirms the distinct marking on the gold watch and the specific damage pattern on the cream card.

**Caption**: An old, blank parchment lies on a rustic wooden desk beside a vintage pocket watch and string of pearls.
![An old, blank parchment lies on a rustic wooden desk beside a vintage pocket watch and string of pearls.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S13-IMG2.png)

---

##### `SCENE_S13:R5` — **CLUE for Q#37, Q#45**

**User**: Now here is a later image of the same prop table after rehearsal traffic.

**Assistant**: Got it. Most of the table remains stable, but one distinctive gold accessory that had been on the left is no longer present.

**Caption**: A vintage theater dressing table is set with a top hat, fan, pearls, and a blank cue card awaiting the next performance.
![A vintage theater dressing table is set with a top hat, fan, pearls, and a blank cue card awaiting the next performance.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S13-IMG3.png)

---

##### `SCENE_S13:R6`

**User**: I won't name that missing item directly later, so keep its visual signature in memory.

**Assistant**: Got it. I'll remember the specific cue on that missing gold item rather than treating it as just another watch.

---

##### `SCENE_S13:R7` — **CLUE for Q#38**

**User**: Here is the wings area near stage left.

**Assistant**: Got it. The wings area includes several visually similar but distinct objects, including a different hat band combination and a black tag that is not attached.

**Caption**: A black top hat with a gold band rests on a wooden stool in a dimly lit backstage area.
![A black top hat with a gold band rests on a wooden stool in a dimly lit backstage area.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S13-IMG4.png)

---

##### `SCENE_S13:R8`

**User**: Exactly. Some of these are distractors. Don't merge them with the main table props just because they share a category or color.

**Assistant**: Understood. I'll separate the clipped versus loose tags, the different hat band combinations, and the cane by handle material.

---

### Session `SCENE_S14` — 2025-09-10

##### `SCENE_S14:R1`

**User**: Now I'm moving to the quick change station and the costume rack area. Some earlier missing things may show up there, mixed with look alikes.

**Assistant**: Understood. I'll compare carefully and avoid assuming identity from rough similarity alone.

---

##### `SCENE_S14:R2` — **CLUE for Q#39, Q#45**

**User**: Here is the quick change station.

**Assistant**: Got it. The quick change station contains a strong candidate match for the missing gold item, plus several similar but clearly distinct objects in bottle, jewelry, card, and cane form.

**Caption**: Vintage dressing table with a golden locket, pearl necklace, and blue potion bottle glowing under warm vanity lights.
![Vintage dressing table with a golden locket, pearl necklace, and blue potion bottle glowing under warm vanity lights.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S14-IMG1.png)

---

##### `SCENE_S14:R3`

**User**: Good. Some of those are traps if you pay attention only to color.

**Assistant**: Understood. I'm tracking engraving, material, coiled versus loose arrangement, corner damage, and handle metal.

---

##### `SCENE_S14:R4` — **CLUE for Q#39, Q#40, Q#45**

**User**: Here is a closer crop of the counter.

**Assistant**: Got it. The close up confirms the match cue on the gold item and clarifies the material and shape differences of the surrounding objects.

**Caption**: Vintage vanity items—a pocket watch, pearls, cane, and blank card—are arranged on a rustic wooden dressing table.
![Vintage vanity items—a pocket watch, pearls, cane, and blank card—are arranged on a rustic wooden dressing table.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S14-IMG2.png)

---

##### `SCENE_S14:R5` — **CLUE for Q#41**

**User**: Now the costume rack zone.

**Assistant**: Got it. The costume rack zone introduces both reappearance candidates and close distractors, including a similar hat, a red handheld object with a different finish and trim, a clipped tag, and a blue bottle with potentially matching material.

**Caption**: A theater dressing room shelf holds a top hat, red fan, and costumes waiting for their cue.
![A theater dressing room shelf holds a top hat, red fan, and costumes waiting for their cue.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S14-IMG3.png)

---

##### `SCENE_S14:R6`

**User**: Notice that one red item there is close in color but not in surface or edge detail.

**Assistant**: Understood. I'll separate the two red foldable props by fabric type and trim structure.

---

##### `SCENE_S14:R7` — **CLUE for Q#41**

**User**: Here is a wider costume rack image.

**Assistant**: Got it. The costume rack state appears locally stable and preserves several detailed distinctions from the original prop table arrangement.

**Caption**: A theater costume rack and prop shelf await the next cue, featuring vintage outfits, a top hat, and a red fan.
![A theater costume rack and prop shelf await the next cue, featuring vintage outfits, a top hat, and a red fan.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S14-IMG4.png)

---

##### `SCENE_S14:R8`

**User**: Quick recap: which missing prop has the strongest reappearance clue so far, and which red item is a look alike rather than a direct match?

**Assistant**: The strongest reappearance clue is for the missing gold watch with the distinctive lid marking, now at the quick change station. The red look alike is the satin fan with ribbon trim in the costume rack zone, which differs from the earlier fan in material and edge detail.

---

### Session `SCENE_S15` — 2025-09-20

##### `SCENE_S15:R1`

**User**: Now I'm going to show the storage cage, and then I'll ask some vague questions.

**Assistant**: Understood. I'll keep the earlier identity cues active and compare them with the storage area items.

---

##### `SCENE_S15:R2`

**User**: Here is the storage cage image.

**Assistant**: Got it. The storage cage contains several items that broadly resemble earlier props, but their detailed features differ in important ways.

**Caption**: A vintage top hat, cane, and pocket watch rest neatly on a metal shelf, evoking an old-world elegance.
![A vintage top hat, cane, and pocket watch rest neatly on a metal shelf, evoking an old-world elegance.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S15-IMG1.png)

---

##### `SCENE_S15:R3`

**User**: Good. Now a vague one: not the gold watch with the plain cover. I mean the other gold one that had a mark on its lid and vanished from the prop table. Which item is that?

**Assistant**: That is the gold pocket watch with the engraved star on the lid, which disappeared from the prop table and later appeared at the quick change station.

---

##### `SCENE_S15:R4`

**User**: Another one: not the red folded prop with the smoother fabric and ribbon like edge. I mean the other red one from the original table. Which is that?

**Assistant**: That is the red velvet hand fan with black lace trim from the original prop table, not the red satin fan with ribbon trim in the costume rack zone.

---

##### `SCENE_S15:R5`

**User**: Here is a close up from the costume rack zone.

**Assistant**: Got it. The close up clarifies the material of the blue bottle, the band color of the hat, and the attachment state of the black tag.

**Caption**: A top hat, red fan, and blue bottle sit on a theater costume shelf labeled "CUE."
![A top hat, red fan, and blue bottle sit on a theater costume shelf labeled "CUE."](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S15-IMG2.png)

---

##### `SCENE_S15:R6` — **CLUE for Q#42**

**User**: Now a final prop table image taken near curtain call.

**Assistant**: Got it. By the final table image, the central hat, damaged card, necklace, and clipped tag remain, while the earlier red fan and blue bottle are no longer in their original table positions.

**Caption**: A vintage magician’s table is set with a top hat, pocket watch, pearls, and a blank, scorched card marked as the next cue.
![A vintage magician’s table is set with a top hat, pocket watch, pearls, and a blank, scorched card marked as the next cue.](../../data/image/Multi-Scene_Visual_Case_Archive_Assistant/S15-IMG3.png)

---

##### `SCENE_S15:R7`

**User**: Another vague one: not the loose black tag on the floor or shelf. I mean the black one that stayed attached in the main handling area and later in the rack zone. Which item is that?

**Assistant**: That is the black cue tag clipped to the prop table and also seen clipped in the costume rack zone, not the loose paper tags seen elsewhere.

---

##### `SCENE_S15:R8`

**User**: Final recap: give me two examples where someone would likely answer incorrectly if they relied only on color or broad object category instead of exact visual cues.

**Assistant**: One example is the star engraved gold watch versus the plain lid gold watch. Another is the velvet fan with black lace trim versus the satin fan with black ribbon trim. A third is the blue glass perfume bottle versus the blue plastic bottle, and a fourth is the clipped black cue tag versus the loose black paper tag.

---

## Questions (clue index)

### Q1 (`X4_Y2`)

- **sessions**: `SCENE_S1`, `SCENE_S2`, `SCENE_S3`
- **clues**: `SCENE_S1:R2`, `SCENE_S2:R2`, `SCENE_S3:R3`
- **question**: Suppose a model tries to identify the backpack only by its dark color and floor-level location. Which additional feature provides the strongest evidence that it is the same moved object across views rather than just another dark object near the door?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The umbrella leaning beside it
  - **B**: The low cardboard box being open
  - **C**: The nearby white adhesive label
  - **D**: The silver star-shaped zipper charm remaining attached ← GT

### Q2 (`X3_Y2`)

- **sessions**: `SCENE_S1`, `SCENE_S2`
- **clues**: `SCENE_S1:R2`, `SCENE_S2:R3`, `SCENE_S2:R4`
- **question**: Which pair would be the worst over-merge if a model ignored both material and object function and only tracked 'small thing near papers or labels'?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The rolled yellow sticky note and the yellow note pad under the monitor stand
  - **B**: The folded receipt in the tray and the cream wall card
  - **C**: The white adhesive label by the door and the cream wall card
  - **D**: The red paper clip in the meeting room and the small red USB drive ← GT

### Q3 (`X3_Y2`)

- **sessions**: `SCENE_S1`, `SCENE_S2`, `SCENE_S3`
- **clues**: `SCENE_S1:R2`, `SCENE_S2:R2`, `SCENE_S2:R4`, `SCENE_S3:R2`, `SCENE_S3:R3`
- **question**: Which of the following is the strongest example of a question where a careless model might overconfidently answer 'same object' even though the evidence only supports 'visually similar and possibly related'?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Whether the backpack by the door is the same backpack seen near the desk leg earlier
  - **B**: Whether the red USB drive in the cabinet is the same missing red desk item
  - **C**: Whether the transparent plastic bag on the desk is related to the earlier cabinet bag
  - **D**: Whether the blue notebook on the box lid is the same as the original dark blue desk notebook ← GT

### Q4 (`X4_Y2`)

- **sessions**: `SCENE_S1`, `SCENE_S2`, `SCENE_S3`
- **clues**: `SCENE_S1:R2`, `SCENE_S2:R2`, `SCENE_S3:R3`
- **question**: Which object is most clearly identified by a combination of color, shape, and attachment state rather than by location alone?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The gray storage box in the cabinet
  - **B**: The umbrella beside the cardboard box
  - **C**: The black mouse on the right side of the desk
  - **D**: The silver star-shaped zipper charm on the backpack ← GT

### Q5 (`X3_Y3`)

- **sessions**: `SCENE_S2`, `SCENE_S3`
- **clues**: `SCENE_S2:R4`, `SCENE_S2:R6`, `SCENE_S3:R4`
- **question**: Which object is best described as remaining in the archive but becoming harder to see because of position and occlusion rather than fully disappearing?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The white adhesive label near the door handle
  - **B**: The black backpack by the door
  - **C**: The black wireless mouse on the desk
  - **D**: The rolled yellow sticky note in the storage cabinet ← GT

### Q6 (`X3_Y3`)

- **sessions**: `SCENE_S1`, `SCENE_S2`, `SCENE_S3`
- **clues**: `SCENE_S1:R5`, `SCENE_S2:R2`, `SCENE_S3:R3`
- **question**: Which object is best supported as having changed from 'not visible in the later desk close-up' to 'present elsewhere nearby' WITHOUT relying on any assumption that two similar blue objects are identical?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The white mug with the blue rim
  - **B**: The black wireless mouse
  - **C**: The cream wall card with the missing lower-right corner
  - **D**: The black backpack with the attached silver star charm ← GT

### Q7 (`X3_Y3`)

- **sessions**: `SCENE_S2`, `SCENE_S3`
- **clues**: `SCENE_S2:R4`, `SCENE_S3:R2`, `SCENE_S3:R4`
- **question**: Which statement about the transparent plastic bag is correct?
- **answer**: D
- **options** (canonical rotation):
  - **A**: It first appeared on the meeting-room table and later moved under the monitor stand
  - **B**: It was attached to the cream wall card and later fell into the doorway box
  - **C**: It remained on the lower cabinet shelf throughout all later images
  - **D**: It was on the cabinet's lower shelf earlier and later appeared on the desk near the keyring ← GT

### Q8 (`X3_Y1`)

- **sessions**: `SCENE_S4`
- **clues**: `SCENE_S4:R2`
- **question**: In the first living-room image, which of the three objects on the coffee table was closest to the front-right corner of the table surface?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The TV remote
  - **B**: The brown wallet
  - **C**: Above choices have same distance
  - **D**: The small plastic-wrapped item ← GT

### Q9 (`X3_Y2`)

- **sessions**: `SCENE_S4`
- **clues**: `SCENE_S4:R2`, `SCENE_S4:R6`
- **question**: Between the first and next-morning living-room images, which exact seat or side of the dining setup had the gray hoodie in the earlier image?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The chair nearest the coffee table
  - **B**: There are no correct choice above
  - **C**: The chair farthest from the camera
  - **D**: The chair nearest the front door ← GT

### Q10 (`X3_Y1`)

- **sessions**: `SCENE_S5`
- **clues**: `SCENE_S5:R2`
- **question**: In the bedroom-desk image, which item sat immediately to the right of the closed black laptop?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The blue mug
  - **B**: The coiled white earphones
  - **C**: The white desk lamp
  - **D**: The brown leather wallet ← GT

### Q11 (`X3_Y1`)

- **sessions**: `SCENE_S5`
- **clues**: `SCENE_S5:R4`, `SCENE_S5:R6`
- **question**: On the hallway-closet middle shelf, which item was nearest to the green rectangular card?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Same distance
  - **B**: The yellow pill bottle
  - **C**: The stacked napkins
  - **D**: The plaid textile ← GT

### Q12 (`X3_Y1`)

- **sessions**: `SCENE_S5`
- **clues**: `SCENE_S5:R7`
- **question**: In the later kitchen image from the afternoon, was the faint circular stain located left of the pill container, right of it, directly in front of it or directly behind of it.?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Left of the pill container
  - **B**: Directly behind of the pill container
  - **C**: Directly in front of the pill container
  - **D**: Right of the pill container ← GT

### Q13 (`X3_Y1`)

- **sessions**: `SCENE_S6`
- **clues**: `SCENE_S6:R2`
- **question**: In the entryway-bench close-up, was the upright blue umbrella leaning closer to the bench frame, the wall, or the nearest pair of shoes?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Closer to the bench frame
  - **B**: Closer to the wall
  - **C**: Closer to the nearest pair of shoes
  - **D**: About equally close to the bench frame and the wall ← GT

### Q14 (`X3_Y1`)

- **sessions**: `SCENE_S6`
- **clues**: `SCENE_S6:R3`
- **question**: In the later living-room image from S6, on which side of the TV remote was the round coaster located?
- **answer**: D
- **options** (canonical rotation):
  - **A**: To the left of the remote
  - **B**: Directly front of the remote
  - **C**: Directly behind the remote
  - **D**: To the right of the remote ← GT

### Q15 (`X3_Y1`)

- **sessions**: `SCENE_S7`
- **clues**: `SCENE_S7:R2`
- **question**: In the first fossil-room image, which right-side item was closest to the front edge of the display surface: the blue shell-shaped object or the black tag marked “C-1127”?
- **answer**: D
- **options** (canonical rotation):
  - **A**: This cannot be determined from the current session. 
  - **B**: The black tag marked “C-1127”
  - **C**: They were aligned at the same front-back depth
  - **D**: The blue shell-shaped object ← GT

### Q16 (`X3_Y1`)

- **sessions**: `SCENE_S7`
- **clues**: `SCENE_S7:R4`
- **question**: In the lower-front fossil-room crop, how much of the blue shell-shaped object was visible to the right of the torn label: only a narrow edge, roughly half, most of the object or whole of the object?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Only a narrow edge
  - **B**: Roughly half
  - **C**: Whole of the object
  - **D**: Most of the object ← GT

### Q17 (`X3_Y2`)

- **sessions**: `SCENE_S7`
- **clues**: `SCENE_S7:R2`, `SCENE_S7:R5`, `SCENE_S7:R7`
- **question**: Between the first fossil-room image and the later fossil-room image, did the green drawstring pouch appear remained unchanged, centered directly behind the rock, shifted slightly left, or shifted slightly right relative to the fossil slab?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Shifted slightly left
  - **B**: Remained unchange
  - **C**: Stayed centered directly behind the rock
  - **D**: Shifted slightly right ← GT

### Q18 (`X3_Y1`)

- **sessions**: `SCENE_S8`
- **clues**: `SCENE_S8:R2`
- **question**: In the maritime gallery case, was the hanging tag “A-209” positioned closer to the blue fish-shaped object or closer to the brass dial instrument?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Closer to the blue fish-shaped object
  - **B**: None of them come close.
  - **C**: Centered roughly between them
  - **D**: Closer to the brass dial instrument ← GT

### Q19 (`X3_Y1`)

- **sessions**: `SCENE_S8`
- **clues**: `SCENE_S8:R4`, `SCENE_S8:R6`
- **question**: On the restoration table, was the metal tool more horizontally aligned with the compass, slightly above it, or slightly below it?
- **answer**: D
- **options** (canonical rotation):
  - **A**: More horizontally aligned with the compass
  - **B**: Slightly above the compass
  - **C**: This cannot be determined from the sessions
  - **D**: Slightly below the compass ← GT

### Q20 (`X3_Y1`)

- **sessions**: `SCENE_S8`
- **clues**: `SCENE_S8:R6`
- **question**: In the restoration-table right-side close-up, was the red-handled brass seal stamp placed nearer the front edge of the table than the drafting tool, farther back than it, or at roughly the same depth?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Nearer the front edge
  - **B**: This cannot be determined from the sessions.
  - **C**: At roughly the same depth
  - **D**: Farther back ← GT

### Q21 (`X3_Y1`)

- **sessions**: `SCENE_S8`
- **clues**: `SCENE_S8:R7`
- **question**: In the storage prep room, was the folded dark green velvet pouch closer to the stacked beige trays, the red wax stick, or the silver knife?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Closer to the red wax stick
  - **B**: Closer to the silver knife
  - **C**: Equidistant from all
  - **D**: Closer to the stacked beige trays ← GT

### Q22 (`X3_Y1`)

- **sessions**: `SCENE_S9`
- **clues**: `SCENE_S9:R1`
- **question**: In the next-morning fossil-room image, was the hanging tag “A-209” vertically higher than the top of the blue fish-shaped object, lower than it, or overlapping its vertical level?
- **answer**: D
- **options** (canonical rotation):
  - **A**: This cannot be determined from the session
  - **B**: Lower than the blue fish-shaped object
  - **C**: Overlapping its vertical level
  - **D**: Higher than the blue fish-shaped object ← GT

### Q23 (`X3_Y1`)

- **sessions**: `SCENE_S9`
- **clues**: `SCENE_S9:R2`
- **question**: In the later restoration-room image, was the small corked glass jar of sand positioned closer to the compass or closer to the blank rectangular label?
- **answer**: D
- **options** (canonical rotation):
  - **A**: This cannot be determined from the sessions
  - **B**: Closer to the blank rectangular label
  - **C**: Centered between them
  - **D**: Closer to the compass ← GT

### Q24 (`X3_Y1`)

- **sessions**: `SCENE_S9`
- **clues**: `SCENE_S9:R7`
- **question**: In the maritime gallery close-up, did the chipped-corner blank label sit more directly in front of the round brass object, more directly in front of the blue ceramic fish, or between them with no clear front alignment to either?
- **answer**: D
- **options** (canonical rotation):
  - **A**: More directly in front of the round brass object
  - **B**: More directly in front of the blue ceramic fish
  - **C**: This cannot be determined from the sessions
  - **D**: Between them with no clear front alignment to either ← GT

### Q25 (`X3_Y2`)

- **sessions**: `SCENE_S7`, `SCENE_S8`
- **clues**: `SCENE_S7:R2`, `SCENE_S8:R2`, `SCENE_S8:R4`, `SCENE_S8:R7`
- **question**: Which room contains the strongest cluster of distractors that could fool a model relying only on rough category labels like 'brass object', 'blue object', and 'blank label'?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The original fossil room
  - **B**: The storage prep room
  - **C**: The restoration table
  - **D**: The maritime gallery ← GT

### Q26 (`X3_Y1`)

- **sessions**: `SCENE_S10`
- **clues**: `SCENE_S10:R2`, `SCENE_S10:R4`
- **question**: In the first main-bench image, which item was closest to the front-left corner of the yellow rack?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The blue-capped tube
  - **B**: The metal tweezers
  - **C**: The blue storage box
  - **D**: The red-capped tube ← GT

### Q27 (`X3_Y1`)

- **sessions**: `SCENE_S10`
- **clues**: `SCENE_S10:R4`
- **question**: In the closer crop of the front bench area, was the missing front-left red-capped tube positioned nearer to the front edge of the bench or nearer to the centerline of the rack?
- **answer**: D
- **options** (canonical rotation):
  - **A**: This cannot be determined from the provided sessions.
  - **B**: Nearer to the centerline of the rack
  - **C**: Exactly centered between the two
  - **D**: Nearer to the front edge of the bench ← GT

### Q28 (`X3_Y1`)

- **sessions**: `SCENE_S10`
- **clues**: `SCENE_S10:R5`
- **question**: In the later main-bench image, was the strip of small clear tubes positioned directly behind the yellow rack, offset to its left, or offset to its right?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Directly front of the yellow rack
  - **B**: Offset to the left of the yellow rack
  - **C**: Offset to the right of the yellow rack
  - **D**: Directly behind the yellow rack ← GT

### Q29 (`X3_Y1`)

- **sessions**: `SCENE_S10`
- **clues**: `SCENE_S10:R7`
- **question**: In the pipette-area image, was the black clipped label closer to which one.
- **answer**: A
- **options** (canonical rotation):
  - **A**: Closer to the red-capped vial ← GT
  - **B**: Closer to the clear microcentrifuge tube
  - **C**: Closer to silver tweezers
  - **D**: About the same distance from the red-capped vial and silver tweezers

### Q30 (`X3_Y1`)

- **sessions**: `SCENE_S11`
- **clues**: `SCENE_S11:R2`, `SCENE_S11:R4`
- **question**: On the first cold-room shelf image, was the loose barcode label placed more in front of the yellow rack, more beside the folded white towels, or midway between those regions?
- **answer**: D
- **options** (canonical rotation):
  - **A**: More in front of the yellow rack
  - **B**: More beside the folded white towels
  - **C**: This cannot be determined from the sessions
  - **D**: Midway between those regions ← GT

### Q31 (`X3_Y1`)

- **sessions**: `SCENE_S11`
- **clues**: `SCENE_S11:R5`
- **question**: In the lower cold-room shelf image, was the strip of five small clear microtubes aligned more closely with the large blue-capped vial on the left or with the metal tweezers on the right?
- **answer**: B
- **options** (canonical rotation):
  - **A**: More closely aligned with the large blue-capped vial
  - **B**: More closely aligned with the metal tweezers ← GT
  - **C**: This cannot be determined from the provided captions alone
  - **D**: Centered equally between them

### Q32 (`X3_Y1`)

- **sessions**: `SCENE_S12`
- **clues**: `SCENE_S12:R2`
- **question**: In the centrifuge-station wide image, which of the two labeled sample vials in the foam rack sat nearer the strip of microtubes: the amber-liquid vial or the pink-liquid vial?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The amber-liquid vial
  - **B**: This cannot be determined from the provided sessions
  - **C**: They were equally close to the strip
  - **D**: The pink-liquid vial ← GT

### Q33 (`X3_Y1`)

- **sessions**: `SCENE_S12`
- **clues**: `SCENE_S12:R4`
- **question**: In the close-up of the right side of the centrifuge station, did the diagonal tweezers point more toward the microtube strip, more toward the sample rack, or more toward the lower edge of the frame?
- **answer**: C
- **options** (canonical rotation):
  - **A**: More toward the microtube strip
  - **B**: More toward the sample rack
  - **C**: More toward the lower edge of the frame ← GT
  - **D**: None of the above

### Q34 (`X4_Y2`)

- **sessions**: `SCENE_S10`, `SCENE_S12`
- **clues**: `SCENE_S10:R2`, `SCENE_S10:R5`, `SCENE_S12:R2`, `SCENE_S12:R4`
- **question**: Comparing the main-bench strip and the centrifuge-station strip, was the blue-filled tube in the same ordinal slot position within the strip, or not?
- **answer**: D
- **options** (canonical rotation):
  - **A**: This cannot be determined from the provided captions alone
  - **B**: No, it occupied a different slot position
  - **C**: The main-bench strip had more blue-filled wells than the centrifuge strip
  - **D**: Yes, it occupied the same ordinal slot position ← GT

### Q35 (`X3_Y1`)

- **sessions**: `SCENE_S13`
- **clues**: `SCENE_S13:R2`
- **question**: In the first main prop-table image, which item sat closest to the front-right corner of the table surface ?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The white paper
  - **B**: The blue bottle
  - **C**: The pearl necklace
  - **D**: The red lace fan ← GT

### Q36 (`X3_Y1`)

- **sessions**: `SCENE_S13`
- **clues**: `SCENE_S13:R4`
- **question**: In the left-half prop-table crop, was the brass pocket watch placed closer to the singed-edged parchment or closer to the pearl necklace?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Centered about equally between them
  - **B**: Closer to the pearl necklace
  - **C**: This cannot be determined from the provided sessions
  - **D**: Closer to the singed-edged parchment ← GT

### Q37 (`X3_Y1`)

- **sessions**: `SCENE_S13`
- **clues**: `SCENE_S13:R5`
- **question**: In the later prop-table image after rehearsal traffic, was the remaining red fan aligned more closely with the center hat, the front-edge 'CUE' card area, or the perfume-bottle cluster?
- **answer**: D
- **options** (canonical rotation):
  - **A**: More closely with the center hat
  - **B**: More closely with the front-edge 'CUE' card area
  - **C**: More closely with the perfume-bottle cluster
  - **D**: The remaining red fan sat on the right side between the center hat and the perfume bottles ← GT

### Q38 (`X3_Y1`)

- **sessions**: `SCENE_S13`
- **clues**: `SCENE_S13:R7`
- **question**: In the wings-area image, was the gold-banded black hat positioned more toward the front edge of the stool seat, more toward the back edge, or centered on the seat?
- **answer**: D
- **options** (canonical rotation):
  - **A**: This cannot be determined from the provided information
  - **B**: More toward the back edge
  - **C**: More toward the front edge
  - **D**: Centered on the seat ← GT

### Q39 (`X3_Y1`)

- **sessions**: `SCENE_S14`
- **clues**: `SCENE_S14:R2`, `SCENE_S14:R4`
- **question**: At the quick-change station, was the blue bottle placed nearer to the watch, the mirror light, the blank card, or the pearl necklace?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Nearer to the mirror light
  - **B**: Nearer to the blank card
  - **C**: Nearer to the pearl necklace
  - **D**: Nearer to the watch ← GT

### Q40 (`X3_Y1`)

- **sessions**: `SCENE_S14`
- **clues**: `SCENE_S14:R4`
- **question**: In the closer quick-change counter crop, was the wooden cane leaning with its handle end nearer the watch side of the counter or nearer the mirror side?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Nearer the watch side
  - **B**: This cannot be determined from the information
  - **C**: The handle and shaft were parallel to the mirror edge
  - **D**: Nearer the mirror side ← GT

### Q41 (`X3_Y1`)

- **sessions**: `SCENE_S14`
- **clues**: `SCENE_S14:R5`, `SCENE_S14:R7`
- **question**: In the costume-rack zone, was the blue glass bottle placed directly behind the red folding fan, offset to one side of it, or separated from it by the hat?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Directly behind the red folding fan
  - **B**: Offset to one side of the red folding fan
  - **C**: No right answer above
  - **D**: Separated from it by the hat ← GT

### Q42 (`X3_Y1`)

- **sessions**: `SCENE_S15`
- **clues**: `SCENE_S15:R6`
- **question**: In the final prop-table image, was the brass pocket watch positioned more to the left of the hat, more in front of it, or more to the right of it?
- **answer**: D
- **options** (canonical rotation):
  - **A**: More to the left of the hat
  - **B**: More in front of the hat
  - **C**: More to the right of the hat
  - **D**: The brass pocket watch was positioned to the left-front of the hat, primarily on its left side. ← GT

### Q43 (`X2_Y3`)

- **sessions**: `SCENE_S1`, `SCENE_S2`, `SCENE_S3`
- **clues**: `SCENE_S1:R2`, `SCENE_S1:R5`, `SCENE_S2:R4`, `SCENE_S3:R4`
- **question**: Where is the small red USB drive in the most recent archive images?
- **answer**: D
- **options** (canonical rotation):
  - **A**: In the desk drawer
  - **B**: On the top-right corner of the desk
  - **C**: It was discarded and is no longer in the archive
  - **D**: On the middle shelf of the storage cabinet, near the front edge ← GT

### Q44 (`X2_Y3`)

- **sessions**: `SCENE_S7`, `SCENE_S8`
- **clues**: `SCENE_S7:R2`, `SCENE_S7:R5`, `SCENE_S8:R4`
- **question**: In the most recent images, where is the small brass compass that was originally on the left side of the fossil display case?
- **answer**: D
- **options** (canonical rotation):
  - **A**: Missing with no reappearance
  - **B**: In the maritime gallery
  - **C**: Still on the left side of the fossil display case
  - **D**: On the restoration table ← GT

### Q45 (`X2_Y3`)

- **sessions**: `SCENE_S13`, `SCENE_S14`
- **clues**: `SCENE_S13:R2`, `SCENE_S13:R4`, `SCENE_S13:R5`, `SCENE_S14:R2`, `SCENE_S14:R4`
- **question**: Where is the gold pocket watch with the engraved star lid currently located in the backstage area?
- **answer**: D
- **options** (canonical rotation):
  - **A**: On the left half of the prop table
  - **B**: Missing with no reappearance
  - **C**: In the costume rack
  - **D**: At the quick-change station ← GT

### Q46 (`X2_Y3`)

- **sessions**: `SCENE_S10`, `SCENE_S11`
- **clues**: `SCENE_S10:R2`, `SCENE_S10:R5`, `SCENE_S11:R5`
- **question**: Where are the bent-tip forceps that were originally on the main lab bench?
- **answer**: D
- **options** (canonical rotation):
  - **A**: On the restoration table in the archive
  - **B**: Missing from all documented images
  - **C**: Still on the main lab bench
  - **D**: On the lower shelf of the cold-room prep area ← GT

### Q47 (`X4_Y3`)

- **sessions**: `SCENE_S7`, `SCENE_S9`
- **clues**: `SCENE_S7:R2`, `SCENE_S7:R5`, `SCENE_S7:R7`, `SCENE_S9:R1`
- **question**: What identification tag number is currently displayed in the fossil room case?
- **answer**: D
- **options** (canonical rotation):
  - **A**: No tag is displayed
  - **B**: F-042
  - **C**: C-1127
  - **D**: A-209 ← GT

### Q48 (`X2_Y3`)

- **sessions**: `SCENE_S2`, `SCENE_S3`
- **clues**: `SCENE_S2:R4`, `SCENE_S2:R6`, `SCENE_S3:R4`
- **question**: Comparing the storage cabinet's middle shelf between its first appearance and the later rearrangement, in which direction did the gray storage box shift?
- **answer**: D
- **options** (canonical rotation):
  - **A**: It shifted slightly to the right
  - **B**: It moved from the middle shelf to the top shelf
  - **C**: Its position did not change
  - **D**: It shifted slightly to the left ← GT

### Q49 (`X3_Y3`)

- **sessions**: `SCENE_S5`, `SCENE_S6`
- **clues**: `SCENE_S5:R2`, `SCENE_S6:R6`
- **question**: How did the spatial arrangement of items on the bedroom desk change between its first and most recent recorded states?
- **answer**: D
- **options** (canonical rotation):
  - **A**: The laptop moved from the center to the far right end
  - **B**: All items remained in the same single row but the desk was rotated
  - **C**: The desk items were removed and replaced by completely different objects
  - **D**: Items shifted from a single row to a center-divided layout with the laptop in the middle ← GT

### Q50 (`X3_Y3`)

- **sessions**: `SCENE_S2`, `SCENE_S3`
- **clues**: `SCENE_S2:R4`, `SCENE_S2:R6`, `SCENE_S3:R4`
- **question**: In the most recent cabinet image, how has the red USB drive's position on the middle shelf changed compared to its initial placement there?
- **answer**: D
- **options** (canonical rotation):
  - **A**: It was placed on the top shelf instead
  - **B**: Its position on the shelf did not change
  - **C**: It moved to the back-right corner of the shelf
  - **D**: It moved closer to the front edge of the shelf ← GT
