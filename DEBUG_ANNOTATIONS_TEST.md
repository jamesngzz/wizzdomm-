# Debug Annotations - Test Instructions

I've added extensive logging to help debug the annotation save/load issues. Please follow these steps:

## Step 1: Test Saving Annotations

1. Open the Grading page with a submission
2. **Open Browser DevTools** (F12 or Cmd+Option+I)
3. Go to the **Console** tab
4. Add an annotation (text, circle, or rectangle)
5. Click "Save Annotations"
6. Look for these console logs:

```
All canvas objects: [...]
Filtered objects (non-background): X
Image dimensions: { imgWidth: XXX, imgHeight: XXX }
Saving X annotations: [...]
Save successful!
```

**What to check:**
- Are annotations being created? (Check "Filtered objects" count)
- Is the payload being generated? (Check "Saving X annotations")
- Is the save succeeding? (Check for "Save successful!" or error)

## Step 2: Check Backend Logs

In your terminal where the Django server is running, look for:

```
=== PUT /items/X/ ===
Request data: {...}
Annotations received: <class 'list'>, length: X
Saved X annotations to item X
=== END PUT ===
```

**What to check:**
- Is the request reaching the backend?
- Is the annotations data formatted correctly?
- Are annotations being saved to the database?

## Step 3: Test Loading Annotations

1. Reload the page (F5)
2. Check the console for:

```
Loading X existing annotations: [...]
✅ Image loaded with X annotations
```

**What to check:**
- Are annotations being retrieved from the database?
- Are they being converted back to canvas objects?

## Step 4: Test PDF Export

1. After saving annotations, click "Export PDF"
2. Check backend terminal for:

```
Page 0: Found X items
  Item Y: source_pages=[0], annotations=Z
  -> Processing Z annotations for item Y
```

3. Open the exported PDF
4. Check if annotations are visible

**What to check:**
- Are items found for the page?
- Do items have annotations in the database?
- Are annotations being processed during PDF generation?

## Common Issues to Look For

### Issue 1: Annotations Not Saving
**Symptoms:**
- "Saving 0 annotations" in console
- OR "No annotations to save" toast

**Cause:** Annotations are filtered out as "grading" or "overlay"

**Fix:** Check that added annotations don't have `isGrading` or `isOverlay` flags

### Issue 2: Save Request Failing
**Symptoms:**
- "Save error" toast
- Network error in DevTools Network tab

**Cause:** API endpoint not reachable or CORS issue

**Fix:** Check Network tab for the PUT request status

### Issue 3: Annotations Not Loading
**Symptoms:**
- Console shows "Loading 0 existing annotations"
- OR annotations array is empty/null

**Cause:** Data not persisted to database

**Fix:** Check backend logs to confirm save succeeded

### Issue 4: Annotations in Wrong Position
**Symptoms:**
- Annotations load but in wrong location

**Cause:** Coordinate normalization issue

**Fix:** Check the normalized coordinates in console logs

### Issue 5: PDF Export Shows No Annotations
**Symptoms:**
- Backend shows "Processing 0 annotations"
- OR PDF is blank

**Possible causes:**
- Annotations not saved to database
- source_page_indices mismatch
- Rendering error in PDF generation

## What to Send Me

If still not working, please send:

1. **Browser Console Logs** (copy all logs from steps 1-3)
2. **Backend Terminal Logs** (copy the PUT request logs)
3. **Screenshot** of the annotations on canvas
4. **Network Tab** screenshot showing the PUT request

This will help me identify exactly where the issue is!

