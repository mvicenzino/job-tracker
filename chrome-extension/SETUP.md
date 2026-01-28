# Stride Chrome Extension — Setup Guide

## Option A: Install from Chrome Web Store (Easiest)

1. Open the extension link shared with you (in Chrome)
2. Click **Add to Chrome**
3. Click **Add Extension** in the popup that appears
4. You'll see the Stride icon in your toolbar — done installing!

Now skip to **Connect to Your Account** below.

---

## Option B: Install Manually

If the extension isn't on the Chrome Web Store yet, follow these steps.

### Step 1: Download the extension

Save the `chrome-extension` folder (the one containing this file) somewhere on your computer — for example, your Desktop or Downloads folder.

### Step 2: Open Chrome Extensions

1. Open Chrome
2. Type `chrome://extensions` in the address bar and press Enter
3. In the top-right corner, flip the **Developer mode** toggle ON (it turns blue)

### Step 3: Load the extension

1. Click the **Load unpacked** button (top-left area)
2. Navigate to the `chrome-extension` folder you saved in Step 1
3. Select the folder and click **Open** / **Select Folder**

### Step 4: Pin it

1. Click the puzzle piece icon in Chrome's toolbar (top-right)
2. Find **Stride - LinkedIn Import** in the list
3. Click the pin icon next to it so it stays visible

---

## Connect to Your Account

You only need to do this once.

### Step 1: Get your API key

1. Log in to Stride at **https://stride-jobs.vercel.app**
2. Click **Settings** in the left sidebar
3. Click **Generate API Key**
4. Click **Copy** next to the key

### Step 2: Paste it into the extension

1. Click the **Stride icon** in your Chrome toolbar
2. Click the **gear icon** (top-right of the popup)
3. **Server URL** should already say `https://stride-jobs.vercel.app` — if it's blank, paste that in
4. **API Key** — paste the key you copied
5. Click **Save**
6. You should see a green success message

---

## How to Use It

1. Go to **LinkedIn** in Chrome
2. Visit any **person's profile**, **company page**, or **job listing**
3. Click the **Stride icon** in your toolbar
4. The extension auto-fills the info from the page
5. Review it, add any notes, then click **Add Contact** / **Add Company** / **Add Job**
6. It goes straight into your Stride dashboard

That's it! Every contact, company, or job you save from LinkedIn shows up in Stride automatically.
