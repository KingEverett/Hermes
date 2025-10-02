#!/bin/bash

# E2E Test Setup Verification Script
# Tests if backend and frontend can start correctly for E2E testing

set -e

echo "🚀 Testing E2E Setup..."

# Test 1: Backend can start
echo "✅ Testing backend startup..."
cd ../../backend
timeout 10 python main.py &
BACKEND_PID=$!
sleep 3

# Check if backend is responding
if curl -s http://localhost:8000/api/v1/projects/ > /dev/null; then
    echo "✅ Backend is responding on port 8000"
else
    echo "❌ Backend not responding"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Kill backend
kill $BACKEND_PID 2>/dev/null || true
sleep 2

# Test 2: Frontend can build and serve
echo "✅ Testing frontend build..."
cd ../frontend/web-app
npm run build

echo "✅ Testing frontend serve..."
timeout 10 npx serve -s build -l 3000 &
FRONTEND_PID=$!
sleep 3

# Check if frontend is responding
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend is serving on port 3000"
else
    echo "❌ Frontend not serving"
    kill $FRONTEND_PID 2>/dev/null || true
    exit 1
fi

# Kill frontend
kill $FRONTEND_PID 2>/dev/null || true

echo "🎉 E2E setup is working correctly!"
echo ""
echo "You can now run E2E tests with:"
echo "  npm run e2e:full    # Full pipeline with built frontend"
echo "  npm run e2e:dev     # Development mode with hot reload"