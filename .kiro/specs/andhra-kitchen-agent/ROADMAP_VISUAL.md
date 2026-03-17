# Andhra Kitchen Agent - Visual Roadmap

Visual diagrams and flowcharts for the implementation roadmap.

---

## 🗺️ Complete Roadmap Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANDHRA KITCHEN AGENT                                 │
│                      8-12 Week Implementation Plan                           │
└─────────────────────────────────────────────────────────────────────────────┘

PHASE 0: FOUNDATION (Week 0) ✅ COMPLETE
┌──────────────────────────────────────────────────────────────┐
│  AWS Infrastructure Setup                                     │
│  • CloudFormation stack                                       │
│  • DynamoDB tables (sessions, prices, reminders)             │
│  • S3 bucket with lifecycle                                   │
│  • API Gateway with rate limiting                             │
│  • Lambda functions (placeholder)                             │
│  • IAM roles and policies                                     │
│  • CloudWatch logging                                         │
│  • Deployment automation                                      │
└──────────────────────────────────────────────────────────────┘
                              ↓
PHASE 1: CORE DATA LAYER (Week 1-2) ⏳ NEXT
┌──────────────────────────────────────────────────────────────┐
│  Data Models & Schemas                                        │
│  • Inventory JSON schema                                      │
│  • Recipe JSON schema                                         │
│  • Shopping List JSON schema                                  │
│  • Python validation utilities                                │
│  • Market prices data (32 entries)                            │
│  • Sample test data                                           │
│  • Environment configuration                                  │
└──────────────────────────────────────────────────────────────┘
                              ↓
PHASE 2: VISION & INVENTORY (Week 2-3) ⏸️
┌──────────────────────────────────────────────────────────────┐
│  Image Analysis                                               │
│  • VisionAnalyzer class (Bedrock Claude 3 Sonnet)           │
│  • Confidence threshold filtering                             │
│  • Error handling & retry logic                               │
│  • KitchenAgentCore class (basic)                            │
│  • POST /upload-image endpoint                                │
│  • POST /analyze-image endpoint                               │
└──────────────────────────────────────────────────────────────┘
                              ↓
PHASE 3: RECIPE GENERATION (Week 3-5) ⏸️
┌──────────────────────────────────────────────────────────────┐
│  Recipe Engine                                                │
│  • RecipeGenerator class (Bedrock Claude 3 Haiku)           │
│  • Memory integration (preferences/allergies)                 │
│  • Low-oil optimization                                       │
│  • Multilingual generation (EN/TE)                            │
│  • Nutrition calculation                                      │
│  • AgentCore orchestration                                    │
│  • Session management                                         │
│  • POST /chat endpoint                                        │
│  • POST /generate-recipes endpoint                            │
└──────────────────────────────────────────────────────────────┘
                              ↓
PHASE 4: SHOPPING & REMINDERS (Week 5-6) ⏸️
┌──────────────────────────────────────────────────────────────┐
│  Shopping Optimization                                        │
│  • ShoppingOptimizer class                                    │
│  • Market price management                                    │
│  • ReminderService class                                      │
│  • ReminderExecutor Lambda                                    │
│  • POST /generate-shopping-list endpoint                      │
│  • Reminder management endpoints                              │
└──────────────────────────────────────────────────────────────┘
                              ↓
PHASE 5: FRONTEND & INTEGRATION (Week 6-8) ⏸️
┌──────────────────────────────────────────────────────────────┐
│  User Interface                                               │
│  • Streamlit app structure                                    │
│  • Chat interface with history                                │
│  • Voice input (Web Speech API)                               │
│  • Image upload UI                                            │
│  • Recipe cards                                               │
│  • Shopping list table                                        │
│  • Reminder notifications                                     │
│  • Language toggle (EN/TE)                                    │
│  • End-to-end workflows                                       │
│  • Mobile responsive design                                   │
└──────────────────────────────────────────────────────────────┘
                              ↓
PHASE 6: FESTIVAL MODE & POLISH (Week 8-10) ⏸️
┌──────────────────────────────────────────────────────────────┐
│  Production Readiness                                         │
│  • Festival calendar data                                     │
│  • FestivalCheckLambda function                              │
│  • Festival mode integration                                  │
│  • Complete documentation                                     │
│  • Test suite (80%+ coverage)                                 │
│  • Performance validation                                     │
│  • Security validation                                        │
│  • Production deployment                                      │
└──────────────────────────────────────────────────────────────┘
                              ↓
                    🎉 PRODUCTION READY 🎉
```

---

## 🎯 MVP Fast Track (5-6 Weeks)

```
┌─────────────────────────────────────────────────────────────┐
│                    MVP FAST TRACK                            │
│              Skip Phase 4 & 6 for Faster Demo               │
└─────────────────────────────────────────────────────────────┘

Week 0: FOUNDATION ✅
    ↓
Week 1-2: DATA LAYER
    ↓
Week 2-3: VISION & INVENTORY
    ↓
Week 3-5: RECIPE GENERATION
    ↓
Week 5-6: FRONTEND & INTEGRATION
    ↓
🚀 MVP READY (Core Features Working)

Later: Add Phase 4 (Shopping) and Phase 6 (Festival Mode)
```

---

## 📊 Task Distribution by Phase

```
Phase 0: Infrastructure
████░░░░░░░░░░░░░░░░ 1 task (1%)

Phase 1: Data Layer
████████████░░░░░░░░ 12 tasks (14%)

Phase 2: Vision
████████░░░░░░░░░░░░ 8 tasks (9%)

Phase 3: Recipes
███████████████░░░░░ 15 tasks (17%)

Phase 4: Shopping
█████████░░░░░░░░░░░ 9 tasks (10%)

Phase 5: Frontend
█████████████████████████████░░░ 29 tasks (33%)

Phase 6: Polish
██████████████░░░░░░ 14 tasks (16%)

Total: 88 tasks
```

---

## 🔄 Dependency Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    CRITICAL PATH                             │
│         (Must be done in this order)                         │
└─────────────────────────────────────────────────────────────┘

Phase 0: Infrastructure
    │
    │ (Required for all phases)
    │
    ├──→ Phase 1: Data Layer
    │        │
    │        │ (Required for Phase 2 & 3)
    │        │
    │        ├──→ Phase 2: Vision
    │        │        │
    │        │        │ (Required for Phase 3)
    │        │        │
    │        │        └──→ Phase 3: Recipes
    │        │                 │
    │        │                 │ (Required for Phase 4)
    │        │                 │
    │        │                 ├──→ Phase 4: Shopping
    │        │                 │        │
    │        │                 │        └──→ Phase 5: Frontend
    │        │                 │                 │
    │        │                 └──→ Phase 5: Frontend (MVP)
    │        │                          │
    │        │                          └──→ Phase 6: Polish
    │        │
    │        └──→ Phase 3: Recipes (can start in parallel)


┌─────────────────────────────────────────────────────────────┐
│                  PARALLEL OPPORTUNITIES                      │
│         (Can be done simultaneously)                         │
└─────────────────────────────────────────────────────────────┘

Week 3-5: Recipe Generation (Main)
    ║
    ╠══► Week 4-5: Start Shopping Optimizer (Parallel)
    ║
    ╚══► Week 4-5: Start Frontend Structure (Parallel)

Week 6-8: Frontend Development (Main)
    ║
    ╠══► Week 6-7: Write Property Tests (Parallel)
    ║
    ╚══► Week 7-8: Write Documentation (Parallel)
```

---

## 🎯 Success Criteria Flow

```
┌─────────────────────────────────────────────────────────────┐
│              VALIDATION CHECKPOINTS                          │
└─────────────────────────────────────────────────────────────┘

Phase 1: Data Layer
    ├─ JSON schemas validate ✓
    ├─ Can store/retrieve from DynamoDB ✓
    ├─ Market prices loaded ✓
    └─ Test data available ✓
         │
         ▼ PROCEED TO PHASE 2
         │
Phase 2: Vision
    ├─ Upload image → Get Inventory JSON ✓
    ├─ Confidence filtering works ✓
    ├─ Response time < 10 seconds ✓
    └─ Error handling works ✓
         │
         ▼ PROCEED TO PHASE 3
         │
Phase 3: Recipes
    ├─ Generate 2-5 recipes ✓
    ├─ Respects allergies/preferences ✓
    ├─ Nutrition accurate (±10%) ✓
    ├─ Multilingual support ✓
    └─ Session management works ✓
         │
         ▼ PROCEED TO PHASE 4 OR 5
         │
Phase 4: Shopping
    ├─ Shopping list generated ✓
    ├─ Prices from markets ✓
    ├─ Reminders scheduled ✓
    └─ Cost calculated ✓
         │
         ▼ PROCEED TO PHASE 5
         │
Phase 5: Frontend
    ├─ All UI components work ✓
    ├─ End-to-end flows work ✓
    ├─ Mobile responsive ✓
    └─ Voice input works ✓
         │
         ▼ PROCEED TO PHASE 6 OR MVP READY
         │
Phase 6: Polish
    ├─ Festival mode works ✓
    ├─ Tests passing (80%+) ✓
    ├─ Documentation complete ✓
    └─ Production validated ✓
         │
         ▼ PRODUCTION READY 🎉
```

---

## 📈 Progress Timeline

```
Week 0  Week 2  Week 3  Week 5  Week 6  Week 8  Week 10
  |       |       |       |       |       |       |
  ▼       ▼       ▼       ▼       ▼       ▼       ▼
  ✅      ⏳      ⏸️      ⏸️      ⏸️      ⏸️      ⏸️
  
  10%     20%     30%     50%     60%     80%     100%
  
  Infra   Data    Vision  Recipe  Shop    Front   Polish
  Done    Layer           Engine          end     
```

---

## 🔑 Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │  Streamlit   │
                    │   Frontend   │
                    └──────┬───────┘
                           │ HTTPS
                           ▼
                    ┌──────────────┐
                    │ API Gateway  │
                    │ Rate Limiting│
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │Kitchen Agent │
                    │     Core     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Bedrock    │
                    │  AgentCore   │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Vision    │  │    Recipe    │  │   Shopping   │
│   Analyzer   │  │  Generator   │  │  Optimizer   │
│              │  │              │  │              │
│ Claude 3     │  │ Claude 3     │  │  + Reminder  │
│  Sonnet      │  │   Haiku      │  │   Service    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│      S3      │  │  DynamoDB    │  │ EventBridge  │
│   (Images)   │  │  (Sessions,  │  │ (Reminders)  │
│              │  │   Prices,    │  │              │
│  24hr TTL    │  │  Reminders)  │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  CloudWatch  │
                  │   Logging    │
                  └──────────────┘
```

---

## 🎨 User Journey Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER JOURNEY                              │
└─────────────────────────────────────────────────────────────┘

1. USER OPENS APP
   │
   ├─→ Streamlit loads
   ├─→ Session created
   └─→ Language selected (EN/TE)
       │
       ▼
2. USER UPLOADS FRIDGE PHOTO
   │
   ├─→ Image uploaded to S3
   ├─→ VisionAnalyzer detects ingredients
   ├─→ Inventory JSON generated
   └─→ Ingredients displayed with confidence
       │
       ▼
3. USER REQUESTS RECIPES
   │
   ├─→ AgentCore queries memory (preferences/allergies)
   ├─→ RecipeGenerator creates 2-5 recipes
   ├─→ Nutrition calculated
   └─→ Recipe cards displayed
       │
       ▼
4. USER SELECTS RECIPE
   │
   ├─→ ShoppingOptimizer compares inventory
   ├─→ Missing ingredients identified
   ├─→ Market prices looked up
   ├─→ Shopping list generated
   └─→ Reminders scheduled
       │
       ▼
5. USER VIEWS SHOPPING LIST
   │
   ├─→ Items grouped by market section
   ├─→ Total cost calculated
   ├─→ User checks off items
   └─→ Reminders displayed
       │
       ▼
6. USER COOKS & ENJOYS! 🍛
```

---

## 💰 Cost Breakdown

```
┌─────────────────────────────────────────────────────────────┐
│                    COST STRUCTURE                            │
└─────────────────────────────────────────────────────────────┘

FREE TIER (Expected Usage)
┌──────────────────────────────────────────────────────┐
│ Lambda:        ~10K requests/month  (Free: 1M)       │
│ DynamoDB:      <1GB storage         (Free: 25GB)     │
│ S3:            <1GB storage         (Free: 5GB)      │
│ API Gateway:   ~10K calls/month     (Free: 1M)       │
│ Bedrock:       ~1K API calls/month  (Paid)           │
│ EventBridge:   ~100 rules/month     (Free: 100)      │
│ CloudWatch:    <5GB logs/month      (Free: 5GB)      │
└──────────────────────────────────────────────────────┘
                    Monthly Cost: $0-5

BEYOND FREE TIER
┌──────────────────────────────────────────────────────┐
│ Bedrock API:   ~$3-5/month                           │
│ DynamoDB:      ~$1-2/month (on-demand)               │
│ Other:         <$1/month                             │
└──────────────────────────────────────────────────────┘
                    Monthly Cost: $5-10
```

---

## 🎯 Feature Completion Matrix

```
┌─────────────────────────────────────────────────────────────┐
│              FEATURE COMPLETION STATUS                       │
└─────────────────────────────────────────────────────────────┘

Feature                    Phase   Status   Priority
─────────────────────────────────────────────────────────────
Infrastructure             0       ✅       CRITICAL
Data Models                1       ⏳       CRITICAL
Image Upload               2       ⏸️       HIGH
Ingredient Detection       2       ⏸️       HIGH
Recipe Generation          3       ⏸️       HIGH
Memory Management          3       ⏸️       HIGH
Multilingual Support       3       ⏸️       HIGH
Session Management         3       ⏸️       HIGH
Shopping Lists             4       ⏸️       MEDIUM
Reminders                  4       ⏸️       MEDIUM
Chat Interface             5       ⏸️       HIGH
Voice Input                5       ⏸️       HIGH
Recipe Cards               5       ⏸️       HIGH
Mobile Responsive          5       ⏸️       HIGH
Festival Mode              6       ⏸️       MEDIUM
Documentation              6       ⏸️       MEDIUM
Testing                    6       ⏸️       MEDIUM
Production Validation      6       ⏸️       MEDIUM

Legend: ✅ Complete | ⏳ In Progress | ⏸️ Pending
```

---

## 🚀 Quick Command Reference

```
┌─────────────────────────────────────────────────────────────┐
│                  QUICK COMMANDS                              │
└─────────────────────────────────────────────────────────────┘

VALIDATE INFRASTRUCTURE
$ ./infrastructure/scripts/validate.sh dev

START PHASE 1
$ kiro execute task 4.1   # Inventory schema
$ kiro execute task 4.2   # Recipe schema
$ kiro execute task 4.3   # Shopping List schema
$ kiro execute task 4.4   # Validation utilities
$ kiro execute task 22.1  # Market prices
$ kiro execute task 22.2  # Environment config
$ kiro execute task 22.3  # Sample data

START PHASE 2
$ kiro execute task 5.1   # VisionAnalyzer
$ kiro execute task 5.2   # Confidence filtering
$ kiro execute task 12.2  # Upload endpoint
$ kiro execute task 12.3  # Analyze endpoint

START PHASE 3
$ kiro execute task 6.1   # RecipeGenerator
$ kiro execute task 9.1   # AgentCore config
$ kiro execute task 12.1  # Chat endpoint
$ kiro execute task 12.4  # Recipes endpoint

CHECK PROGRESS
$ cat .kiro/specs/andhra-kitchen-agent/tasks.md | grep "\\[x\\]" | wc -l
```

---

**Last Updated**: Phase 0 Complete  
**Current Phase**: Phase 1 - Core Data Layer  
**Next Milestone**: Data Foundation (Week 2)  
**Overall Progress**: 10%
