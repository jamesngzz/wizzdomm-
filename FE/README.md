# Welcome to your Lovable project

## Project info

**URL**: https://lovable.dev/projects/e1b956a2-90ba-42c4-85ca-b7fe852f0303

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/e1b956a2-90ba-42c4-85ca-b7fe852f0303) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/e1b956a2-90ba-42c4-85ca-b7fe852f0303) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/features/custom-domain#custom-domain)

## Local setup with backend

### Development Setup

The frontend uses Vite's proxy to forward API requests to the Django backend:
- Frontend dev server: `http://127.0.0.1:8080`
- Backend Django server: `http://127.0.0.1:8000`
- API calls use relative paths (`/api`) which are automatically proxied to Django
- Media files (`/media`) are also proxied to Django
- WebSocket connections (`/ws`) are proxied to Django

### Running Locally

1. Start the Django backend (in `new/backend/`):
```bash
python manage.py runserver 8000
```

2. Start the frontend dev server (in `FE/`):
```bash
npm i
npm run dev
```

3. Access the app at `http://127.0.0.1:8080`

### Environment Variables (optional)

You can override the defaults by creating a `.env` file:

```
# Override API URL (not needed in development)
VITE_API_URL=/api

# Override WebSocket URL (not needed in development)
VITE_WS_URL=ws://127.0.0.1:8080/ws/notifications/
```

**Note:** In development, you should keep the default relative paths to leverage Vite's proxy. Only override these in production or if you need to point to a different backend.
