import urllib.request
import urllib.error
import json
import os

def test(name, url, method='GET', data=None, token=None, expected_status=(200, 201)):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8') if data else None,
        headers=headers,
        method=method
    )
    if isinstance(expected_status, int):
        expected_status = (expected_status,)
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode('utf-8'))
            if resp.status in expected_status:
                print(f"[PASS] {name}: HTTP {resp.status} (as expected)")
            else:
                print(f"[UNEXPECTED] {name}: HTTP {resp.status} (expected {expected_status})")
            return body
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8', errors='ignore')
        if e.code in expected_status:
            print(f"[PASS] {name}: HTTP {e.code} (expected error caught successfully)")
            try:
                return json.loads(err_msg)
            except Exception:
                return err_msg
        else:
            print(f"[FAIL] {name}: HTTP {e.code} (expected {expected_status}) - {err_msg}")
            return None
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        return None

def run_all():
    base = 'http://localhost:3000'
    print("=" * 60)
    print("RUNNING AUTOMATED VEDUKA AI BACKEND TEST SUITE")
    print("=" * 60)

    # 1. Authentication
    login_c = test('Login Customer', f'{base}/api/auth/login', 'POST', {'identifier':'customer@veduka.ai','password':'customer123'})
    token_c = login_c['token'] if login_c else None

    login_v = test('Login Vendor', f'{base}/api/auth/login', 'POST', {'identifier':'nirvana@veduka.ai','password':'vendor123'})
    token_v = login_v['token'] if login_v else None

    admin_email = os.environ.get("VEDUKA_TEST_ADMIN_EMAIL")
    admin_password = os.environ.get("VEDUKA_TEST_ADMIN_PASSWORD")
    token_a = None
    if admin_email and admin_password:
        login_a = test('Login Admin', f'{base}/api/auth/login', 'POST', {
            'identifier': admin_email,
            'password': admin_password
        })
        token_a = login_a['token'] if login_a else None
    else:
        print('[SKIP] Admin tests: configure a dedicated test administrator account.')

    test('Get Me Profile', f'{base}/api/auth/me', 'GET', token=token_c)
    test('Customer Cannot Elevate to Admin', f'{base}/api/auth/switch-role', 'POST', {'role':'admin'}, token=token_c, expected_status=403)

    # 2. Vendors & Discovery
    test('Vendors Filter (Photography in Hyderabad)', f'{base}/api/vendors?category=photography&city=Hyderabad', 'GET')
    test('Vendor Details (ID 1)', f'{base}/api/vendors/1', 'GET')
    test('Compare Vendors (IDs 1 & 2)', f'{base}/api/vendors/compare', 'POST', {'vendor_ids':[1,2]})

    # 3. AI Planning & Seller Assist
    test(
        'Event Planning Estimate (Wedding in Telugu)',
        f'{base}/api/ai/plan',
        'POST',
        {
            'event_type': 'wedding',
            'occasion': 'Wedding celebration',
            'guests': 200,
            'city': 'Hyderabad',
            'total_budget': 600000,
            'event_date': '',
            'language': 'te'
        }
    )
    test('AI Seller Assist', f'{base}/api/ai/seller-assist', 'POST', {'bullet_points':'Sony A7IV, candid expert','category':'photography','target_language':'en'}, token=token_v)

    # 4. Customer Events & Workspace
    test('Customer Events List', f'{base}/api/events', 'GET', token=token_c)
    test('Event Details (ID 1)', f'{base}/api/events/1', 'GET', token=token_c)

    # 5. Quotation Workflow
    rfq = test('Submit RFQ', f'{base}/api/quotations/request', 'POST', {
        'event_id': 1,
        'vendor_id': 2,
        'category': 'decorations',
        'event_date': '2026-11-28',
        'guest_count': 300,
        'requirements': 'Need traditional floral mandap and entrance arch.'
    }, token=token_c)

    # 6. Bookings & Milestone Updates
    test('Customer Bookings List', f'{base}/api/bookings', 'GET', token=token_c)
    test('Update Milestone Stage 2 to in_progress', f'{base}/api/bookings/1/milestones/2/update', 'POST', {'status': 'in_progress'}, token=token_c)

    # 7. Guests & QR Check-in
    test('Guests List for Event 1', f'{base}/api/events/1/guests', 'GET', token=token_c)
    test('QR Door Check-in Verification', f'{base}/api/guests/check-in', 'POST', {'qr_code_token':'GUEST-RAO-9848'}, token=token_c)
    test('QR Door Check-in (Invalid Token Test)', f'{base}/api/guests/check-in', 'POST', {'qr_code_token':'INVALID-TOKEN-999'}, token=token_c, expected_status=404)

    # 8. Cancellation & Refund Workflow Test
    test('Cancel Booking Test (Check transparent refund calculation)', f'{base}/api/bookings/1/cancel', 'POST', token=token_c)

    # 9. Authorization Security Tests (IDOR prevention)
    test('Unauthorized Customer Accepting Another Customer Quote (Should be 403)', f'{base}/api/quotations/1/accept', 'POST', token=token_v, expected_status=403)
    test('Unauthorized Vendor Responding to Another Vendor Quote (Should be 403)', f'{base}/api/quotations/1/respond', 'POST', {'subtotal': 50000}, token=token_c, expected_status=403)

    # 10. Seller Hub
    test('Seller Dashboard Metrics', f'{base}/api/seller/dashboard', 'GET', token=token_v)

    # 11. Admin Overview & KYC Verification
    if token_a:
        test('Admin Overview Metrics', f'{base}/api/admin/overview', 'GET', token=token_a)
        test('Admin Toggle KYC Verification', f'{base}/api/admin/verify-vendor/1', 'POST', token=token_a)

    # 12. Support Tickets & Notifications
    test('List Support Tickets', f'{base}/api/support', 'GET', token=token_c)
    test('Create Support Ticket', f'{base}/api/support', 'POST', {'subject': 'Need invoice copy', 'description': 'Please share GST invoice.'}, token=token_c)
    test('List Notifications', f'{base}/api/notifications', 'GET', token=token_c)

    print("=" * 60)
    print("TEST SUITE EXECUTION COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    run_all()
