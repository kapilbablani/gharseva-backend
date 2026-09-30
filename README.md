# GharSeva - Home Services Marketplace

**"घर के काम, आसान समाधान"**

---

## Our Vision

GharSeva is a trusted digital platform where customers can easily book verified local service professionals for all their home needs—from repairs and maintenance to full construction projects.

### Why GharSeva?
- **Verified Professionals Only** - Every service provider is checked and verified
- **Transparent Pricing** - Know the cost upfront
- **Complete Home Solution** - One app for all home-related needs
- **Local, Personal Service** - Professionals from your area who understand local needs

---

## Launch Journey

### Starting Point: Dewas, Madhya Pradesh

**Phase 0 (Weeks 1-3): Foundation**
- Platform name and branding finalized
- 20-30 verified electricians onboarded
- Initial target: 200-500 customers in Dewas
- Focus on one service category: **Electrician** (repair + fixed-price installation)

**Future Expansion**: Dewas → Ujjain → Indore → Ratlam/Mandsaur → Entire Madhya Pradesh

---

## What's Available When?

---

# PHASE 1: THE BASICS (In Progress)
**"Book a Verified Electrician in Your Area"**

Phase 1 focuses on **three roles**: Customer, Electrician, and Admin. Single service category (Electrician) with two work types: Repair and Service.

## Currently Implemented

### For Customers

**What's Working:**
1. **Sign up & Authentication**
   - Register via Cognito
   - Login/logout with JWT tokens
   - Account verified by role assignment (Cognito Groups)

2. **Browse & Book Services**
   - View repair issues (General repair ₹300, AC repair ₹1000, Refrigerator repair ₹500, Mixer grinder repair ₹500)
   - View service items (Fan installation ₹1000, AC installation ₹4000, AC gas filling ₹5000, Switchboard installation ₹800)
   - Select any combination of repair issues and service items
   - Total price calculated automatically (sum of all items)
   - Confirmation before booking

3. **After Booking**
   - Order placed in "pending_assignment" status
   - System automatically creates dispatch rounds to find matching electricians
   - Order splits into segments by specialization for flexible assignment
   - View all your orders and their current status

**Coming Soon in Phase 1:**
- Address/location confirmation
- Date & time slot selection
- Real-time electrician tracking
- Payment processing (UPI, Card, Cash)
- Rating and review system
- Chat/call support

### For Electricians

**What's Working:**
1. **Sign up & Authentication**
   - Register via Cognito
   - Login/logout with JWT tokens
   - Account verified by role assignment (Cognito Groups)

2. **Set Your Skills**
   - Declare specializations you can handle (e.g., general_repair, ac_repair, fan_installation, ac_installation, etc.)
   - Update your skills anytime
   - System uses this to send you matching jobs

3. **Receive & Accept Jobs**
   - When an order matches your skills, you're added to a dispatch round
   - Accept or skip rounds that are offered to you
   - When you accept, all segments in that round are assigned to you
   - View details of accepted segments (work type, price, customer info)

**Coming Soon in Phase 1:**
- Electrician profile (photo, experience, service area)
- Government ID & address verification (KYC)
- Payment tracking and bank transfers
- Job status updates (On the way → In progress → Completed)
- Photo upload for completed work
- Rating system

### For Admin (You)

**What's Working:**
- Database tables for users, orders, segments, electricians, skills, dispatch rounds
- API endpoints for managing the system
- Service catalog management (repair issues and service items)
- Order creation and assignment workflow
- Dispatch system that automatically groups and broadcasts rounds

**Coming Soon in Phase 1:**
- Admin dashboard with overview stats
- Electrician verification workflow (KYC approval/rejection)
- Customer complaint handling
- Booking oversight and cancellation management
- Reports and analytics

---

# PHASE 2: MORE CATEGORIES & ENHANCED EXPERIENCE (Weeks 13-20)
**"Better Choices, Better Control"**

Phase 2 is where GharSeva expands beyond electricians into a true multi-category marketplace, and adds the features that make repeat use easier for everyone.

### New Service Categories
- Plumber
- Mason (Rajmistri)
- Carpenter
- Painter

### For Customers - New Features

1. **Multiple Service Options**
   - Get quotes from multiple providers across categories
   - Compare prices before choosing
   - Schedule future appointments in advance

2. **Preferred Providers**
   - Save your favorite professionals
   - Get priority when booking
   - Request the same person for repeat work

3. **Customer Support**
   - In-app chat with support team
   - Help with cancellations or disputes
   - Refund processing

### For Providers (all categories) - New Features

1. **Work Availability Calendar**
   - Set your availability (which days/times you work)
   - Block off busy days
   - Set emergency availability hours

2. **Earnings Dashboard**
   - Track total earnings
   - See payment history
   - Understand commission breakdown

3. **Customer Reviews Section**
   - View detailed customer feedback
   - Respond to reviews
   - Improve your service based on feedback

4. **Featured Provider Option**
   - Appear at the top of provider lists
   - Pay monthly subscription to get more visibility
   - Boost bookings from increased visibility

### For Admin - New Features

1. **Advanced Provider Verification**
   - Credit score checking
   - Background verification
   - Insurance verification (if available)

2. **Complaint Management System**
   - Track all customer complaints
   - View complaint resolution timeline
   - Suspend providers for serious issues

3. **Commission Settings**
   - Adjust commission rates
   - Run promotional offers
   - Track revenue by provider and category

4. **Performance Analytics**
   - Which service categories are most popular
   - Which providers have the highest ratings
   - Peak booking times

---

# PHASE 3: CONSTRUCTION & SPECIALIZATION (Weeks 21-30)
**"For Bigger Projects Too"**

### For Customers - New Services

1. **New Professional Categories**
   - Civil Contractors
   - Architects
   - Structural Engineers
   - Interior Designers
   - Tile & Flooring specialists
   - POP/Gypsum workers

2. **Project-Based Booking**
   - Upload project photos/plans
   - Describe scope of work
   - Get detailed quotes from multiple contractors
   - Track multi-day/multi-week projects

3. **Work Progress Tracking**
   - Photo updates from site
   - Progress milestones
   - Payment schedules for large projects

4. **Renovation Packages**
   - "Complete Bathroom Renovation"
   - "Kitchen Makeover"
   - "Full House Painting"
   - Bundles include multiple professionals coordinated by GharSeva

### For Service Providers - New Opportunities

1. **More Categories**
   - Apply for construction-related services
   - Build your portfolio with new projects

2. **Team Management** (for contractors)
   - Add sub-contractors/workers
   - Manage their reviews and ratings
   - Assign jobs to your team

3. **Secure Payments for Big Projects**
   - GharSeva holds payment in escrow
   - Release payment on milestones
   - Dispute resolution for project disputes

### For Admin - New Controls

1. **Project Management**
   - Track large, multi-phase projects
   - Manage timelines and delays
   - Handle more complex disputes

2. **Contractor Verification**
   - Insurance verification
   - License verification (where applicable)
   - Past project references

3. **Quality Assurance**
   - Site visit reviews by admin
   - Photo-based progress verification
   - Customer satisfaction for complex projects

---

# PHASE 4: COMPLETE HOME ECOSYSTEM (Future)
**"Everything Your Home Needs in One Place"**

### For Customers

1. **Materials Marketplace**
   - Buy cement, steel, bricks, tiles, paint
   - Get supplier recommendations
   - Integrated pricing with service bookings

2. **Home Maintenance Plans**
   - Monthly maintenance subscriptions
   - Regular cleaning, inspection, repairs
   - Preventive care alerts

3. **Home Insurance Integration**
   - Link insurance claims to repairs
   - Get verified service providers for insurance-covered work
   - Automatic documentation for claims

4. **Home Design Planning**
   - Virtual consultations with architects
   - 3D visualizations of renovation plans
   - Material selections and pricing

### For Service Providers

1. **Material Supplier Partnerships**
   - Recommend materials to customers
   - Earn commission on material sales
   - Bulk discounts for frequent projects

2. **Advanced Certification**
   - Training programs
   - Certification badges
   - Premium provider status

### For Admin

1. **Marketplace Commission**
   - Earn from service commissions
   - Earn from material sales
   - Subscription fees from premium providers

2. **Business Analytics**
   - Predictive demand (which services will be needed)
   - Customer lifetime value tracking
   - Provider performance benchmarks

---

## Current Service Pricing (Phase 1 - Electrician)

### Repair Issues
- General repair: ₹300
- AC repair: ₹1,000
- Refrigerator repair: ₹500
- Mixer grinder repair: ₹500

### Service Items (Installation/Fixed-Scope Work)
- Fan installation: ₹1,000
- AC installation: ₹4,000
- AC gas filling: ₹5,000
- Switchboard installation: ₹800

**How Pricing Works:**
- Customers select any combination of repair issues and service items
- Final price = sum of all selected items
- One payment per order, regardless of number of items

### For Electricians (Coming Soon)

**How You Earn**
- GharSeva will take 10% commission
- You keep 90% of the job price
- Direct payment to your bank account

**Optional: Premium Provider Plan (Future)**
- Monthly subscription: ₹500-1000
- Get priority in provider listings
- More bookings from visibility boost

---

## How We Protect Everyone

### Verification Process (No Unverified Electricians)

Every electrician must complete:
- ✅ Mobile number verification
- ✅ Government ID verification (Aadhaar/Voter ID/License)
- ✅ Address verification
- ✅ Work experience documentation
- ✅ Work photo portfolio review
- ✅ Reference checks (past work)

### Quality Assurance

1. **Rating System** (After every job)
   - Work quality: Did they do it well?
   - Behavior: Were they professional and courteous?
   - Time: Were they on time?
   - Price: Was it fair?

2. **Provider Monitoring**
   - Electricians below 3.5 stars get warnings
   - Electricians below 3 stars may be suspended
   - Excellent electricians (4.5+ stars) get promoted

3. **Customer Support**
   - 24/7 complaint resolution
   - Refunds if service is unsatisfactory
   - Dispute mediation

---

## Emergency Services

**Coming in Phase 1**

When you need urgent electrical help:
- 🚨 EMERGENCY button in the app (to be implemented)
- Premium service fee for immediate response
- Available for:
  - Sudden power outages
  - Sparking/short-circuit issues
  - Critical electrical repairs

## API Setup & Development

### Prerequisites

- Python 3.10+
- PostgreSQL (for production) or SQLite (for development)
- AWS Cognito configured (for authentication)
- Environment variables set (.env file)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd gharseva-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file with your Cognito credentials:

```env
COGNITO_DOMAIN=your-cognito-domain
COGNITO_CLIENT_ID=your-client-id
COGNITO_REGION=us-east-1
DATABASE_URL=sqlite:///./gharseva.db  # or postgresql://user:pass@localhost/gharseva
```

### Run the Backend

```bash
# Start the FastAPI server
uvicorn app.main:app --reload --port 8000

# The API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### API Endpoints Overview

**Authentication**
- `GET /auth/me` - Get current user claims
- `POST /auth/logout` - Logout from Cognito

**Services**
- `GET /services` - Get all repair issues and service items

**Orders (Customer)**
- `POST /orders` - Create a new order
- `GET /orders/me` - List your orders

**Electricians**
- `POST /electricians/me/skills` - Set your specializations
- `GET /electricians/me/skills` - Get your specializations
- `POST /electricians/jobs/rounds/{round_id}/accept` - Accept a dispatch round

**Users**
- `POST /users/me` - Create/update your profile

### Database

- Automatically initialized on app startup via `Base.metadata.create_all()`
- Development: SQLite file-based database
- Production: PostgreSQL recommended
- Seeded with default catalog (repair issues and service items)

## Tech Stack

- **Framework**: FastAPI (async Python web framework)
- **Authentication**: AWS Cognito (JWT-based with RS256 signature validation)
- **Database**: SQLAlchemy ORM with SQLite (dev) / PostgreSQL (prod)
- **Job Scheduling**: APScheduler (for background tasks like dispatch expiration)
- **Config Management**: Pydantic settings with environment variables
- **Python Version**: 3.10+

## Project Structure

```
app/
├── main.py                    # FastAPI app, DB init, catalog seeding
├── core/
│   ├── config.py             # Settings from .env
│   ├── security.py           # Cognito token verification & auth deps
│   └── dispatch.py           # Order dispatch & round creation logic
├── db/
│   ├── models.py             # SQLAlchemy models (User, Order, Segment, etc)
│   └── session.py            # Database session management
└── api/routes/
    ├── auth.py               # /auth/me, /auth/logout
    ├── users.py              # /users/me
    ├── services.py           # /services (catalog)
    ├── orders.py             # /orders, /orders/me
    └── electricians.py       # Electrician skills & round acceptance
```

---

## Our Competitive Edge

Unlike other job platforms, GharSeva isn't just about one-off gig work.

**Our Unique Positioning:**
- Starts narrow and verified (electricians only) to build trust before expanding categories
- Long-term vision: From new home planning → construction → maintenance
- Local expertise combined with digital trust
- Can support both small jobs AND large construction projects, eventually

**Why This Matters:**
- A customer's first trust-building interaction with GharSeva is a simple, reliable electrical repair or install
- Same customer stays on the platform as more categories and construction services are added
- One trusted relationship for all home needs, built one solid category at a time

---

## Business Model (How GharSeva Makes Money)

### Phase 1-2 Revenue
1. **Commission**: 10% of each service job
2. **Booking Fee**: ₹20-50 per premium booking
3. **Featured Provider Subscription**: ₹500-1000/month

### Phase 3+ Revenue
4. **Construction Project Commissions**: 15% on large projects
5. **Material Marketplace**: 8-12% commission on sales
6. **Maintenance Plans**: Monthly subscriptions

---

## Development Timeline

| Phase | Timeline | Status |
|-------|----------|--------|
| **Foundation** | Week 1-3 | ✅ Complete - Backend setup, database, auth configured |
| **Core APIs** | Week 4-8 | 🔄 In Progress - Orders, dispatch, electrician skills |
| **Testing & Verification** | Week 9-11 | ⏳ Upcoming - Beta testing, electrician KYC workflow |
| **Launch Prep** | Week 12 | ⏳ Upcoming - Performance, payment integration, notifications |
| **🎉 Dewas Launch** | Week 13+ | ⏳ Planned - Marketing, customer acquisition |

---

## How We'll Find Customers Initially

### Direct Outreach
- Local hardware and electrical shops
- Housing societies
- Office complexes
- Residential neighborhoods

### Digital Marketing
- Instagram & Facebook ads targeting Dewas
- Google Business listing (for local search)
- WhatsApp broadcast messages
- YouTube tutorials for booking

### Word of Mouth
- Referral bonuses for satisfied customers
- Incentives for electricians to recommend the platform

---

## Initial Focus: Electrician Only

Phase 1 deliberately narrows to a single category so the app, the verification process, and the operations can be gotten right before scaling to more categories:

1. **Electrician** - Switch/outlet problems, fan and AC repair, wiring issues, fixed-price installations

This single category has frequent, repeat demand—ideal for a first, controlled launch. Plumber, Mason, Carpenter, and Painter follow in Phase 2 once the core experience (booking, verification, payments, ratings) is proven.

---

## What Customers Will Experience

### Customer Journey (Phase 1 - Currently Available)

**Step 1: Sign Up & Login**
- Register with email via Cognito
- Login to access the app
- Get verified as a customer

**Step 2: Browse Services**
- See all available repair issues and service items
- View prices for each option

**Step 3: Create an Order** (Currently Working)
- Select one or more repair issues (e.g., "General repair ₹300", "AC repair ₹1000")
- Select one or more service items (e.g., "Fan installation ₹1000")
- System calculates total price automatically
- Confirm and place the order

**Step 4: Automatic Dispatch**
- Order is sent to matching electricians based on the services needed
- System waits for an electrician to accept the round

**Coming Soon:**
- Choose date and time slot for the service
- Upload photos/description of the issue
- Confirm delivery address
- Pay via UPI, Card, or Cash
- Receive real-time updates when electrician accepts, is on the way, and arrives
- Rate the electrician after completion (1-5 stars)

---

## What Electricians Will Experience

### Electrician Journey (Phase 1 - Currently Available)

**Step 1: Sign Up & Login** (Working)
- Register with email via Cognito
- Login to the app
- Get verified as an electrician

**Step 2: Declare Your Skills** (Currently Working)
- Set your specializations (e.g., general_repair, ac_repair, fan_installation, ac_installation, etc.)
- Update anytime as you gain new skills
- System uses this to send you matching jobs

**Step 3: Receive & Accept Jobs** (Currently Working)
- When orders match your specializations, you're added to dispatch rounds
- View the details of the round: what needs to be done and the total amount
- Accept or skip each round
- When you accept, you get all the segments in that round
- See the breakdown: which repairs/installations and their prices

**Coming Soon:**
- Verify your profile: government ID, address, work portfolio
- Get a "Verified" badge after admin approval
- Receive real-time notifications for new job opportunities
- Update job status as you work (On the way → In progress → Completed)
- Upload photos of completed work
- Track your earnings and receive payments to your bank account
- See your rating score and customer reviews
- Get more job requests as your rating improves

---

## Not Yet Implemented

### Still Being Built in Phase 1
- Electrician profile verification (KYC, government ID, address verification)
- Admin dashboard and verification workflow
- Payment processing (UPI, Card, Cash)
- Job completion tracking and work photo uploads
- Customer rating and review system
- Real-time job notifications (SMS/push/email)
- Job status updates (On the way → In progress → Completed)
- Chat/call support between customer and electrician
- Address and location management for customers
- Time slot selection and booking scheduling
- Customer complaint handling and dispute resolution

### Phase 2+ (Future)
- Other service categories: Plumber, Mason, Carpenter, Painter
- Multiple service items per segment (currently stores only first item per specialization)
- Electrician location-based matching and availability calendars
- Featured provider subscription and premium listings
- Construction project bidding (Phase 3)
- Material marketplace (Phase 4)
- Home design consultations (Phase 4)
- Team management for contractors (Phase 3)
- Insurance integration

We're intentionally keeping Phase 1 to one category and core features so we can get reliability and quality right before expanding. Perfect reliability > lots of features.

---

## Success Metrics (Phase 1)

### Development Milestones (In Progress)
- Core APIs complete and tested: auth, orders, dispatch, electrician skills
- Cognito integration working for customer and electrician signup/login
- Database schema finalized with all Phase 1 models
- Dispatch algorithm handles segment grouping and round creation
- Background job processing for expired rounds

### Launch Targets (For Dewas)

**Customer Metrics**
- 500+ active customers by end of Phase 1
- 100+ completed bookings per week
- 4.3+ average rating from reviews

**Electrician Metrics**
- 20-30 verified electricians onboarded
- 70%+ actively accepting job rounds
- Average ₹15,000+ per electrician per month

**Business Metrics**
- ₹1-2 lakh monthly revenue (single-category scale)
- 10% customer repeat booking rate
- 95%+ job completion rate

---

## Questions from Users/Providers?

**For Customers:**
- "How is my payment secured?" → Escrow-style flow ensures payment is only released after work confirmation
- "What if service is bad?" → Full refund option + electrician suspension for repeated issues
- "Do I need to pay upfront?" → Configurable, most bookings support payment after service completion
- "Can I book multiple repairs and an installation together?" → Yes, select any combination of Repair and Service items and pay once for the combined total
- "Emergency at night?" → Yes, emergency electrical services available with premium fee

**For Electricians:**
- "Will I get enough jobs?" → Depends on location and ratings. Active electricians average 3-4 jobs/week initially
- "How do I get paid?" → Direct bank transfer within 2 hours of job completion
- "What if customer disagrees on price?" → Repair visit charge and Service prices are fixed and shown to the customer before booking, so pricing is clear before work starts
- "Can I work with my team?" → Phase 1: Solo only. Phase 3: Yes, can add team members

---

## One More Thing: The Bigger Vision

GharSeva isn't just a job platform. Eventually:

**Full Home Journey on GharSeva:**

*Building Your New Home:*
Plot Selection → Architect Design → Structural Plan → Contractor Selection → Construction → Electrical → Plumbing → Flooring → Painting → Interior Design

*Maintaining Your Existing Home:*
Repair → Maintenance → Cleaning → Plumbing → Electrical → Painting → Renovation

**One platform. Complete trust. Local professionals. Fair prices.**

Phase 1 is the first, deliberately narrow step toward that vision: prove the model with Customer, Electrician, and Admin roles around a single trusted category, then expand.

---

**Phase 1 launches in Week 13. Are you ready to be part of Dewas' most trusted home service platform?**

*घर का काम, GharSeva से। Home Service, Made Simple.*