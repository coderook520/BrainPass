#!/bin/bash
# BrainPass Installation Script

set -e

echo "🧠 BrainPass Installer"
echo "======================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python version: $PYTHON_VERSION"

# Create directories
echo "📁 Creating directories..."
mkdir -p ~/BrainPass/{vault/{daily,topics,people,projects,sources},cache}

# Copy config if not exists
if [ ! -f ~/BrainPass/config/.env ]; then
    echo "⚙️  Copying .env.example to .env..."
    cp ~/BrainPass/config/.env.example ~/BrainPass/config/.env
    echo "📝 Please edit ~/BrainPass/config/.env with your API keys"
fi

# Copy identity files if not exists
if [ ! -f ~/BrainPass/config/identity/SOUL.md ]; then
    echo "📄 Copying SOUL.md.template to SOUL.md..."
    cp ~/BrainPass/config/identity/SOUL.md.template ~/BrainPass/config/identity/SOUL.md
    echo "📝 Please edit ~/BrainPass/config/identity/SOUL.md with your agent's identity"
fi

# Make librarian executable
chmod +x ~/BrainPass/src/librarian.py

# Create systemd service file
echo "🔧 Creating systemd service..."
cat > ~/.config/systemd/user/brainpass-librarian.service << 'EOF'
[Unit]
Description=BrainPass Librarian — Agent Memory Service
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=5
EnvironmentFile=%h/BrainPass/config/.env
ExecStart=/usr/bin/python3 %h/BrainPass/src/librarian.py serve
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

# Reload systemd
systemctl --user daemon-reload

echo ""
echo "✅ BrainPass installed!"
echo ""
echo "Next steps:"
echo "1. Edit ~/BrainPass/config/.env with your API keys"
echo "2. Edit ~/BrainPass/config/identity/SOUL.md with your agent's identity"
echo "3. Start the service: systemctl --user start brainpass-librarian"
echo "4. Check status: curl http://127.0.0.1:7778/status"
echo ""
echo "For Obsidian integration:"
echo "- Open Obsidian → 'Open another vault' → Select ~/BrainPass/vault/"
echo ""
