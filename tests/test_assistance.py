from test_app import owner, post


def test_assistance_subscription_bundle_and_review():
    customer = owner()
    path = '/api/billing/orders'
    form = {'kind': 'assistance', 'client': 'assist', 'email': 'shop@example.com', 'details': {
        'web': {'reference': 'example.com', 'access': '가능', 'platform': '카페24'},
        'naver': {'reference': 'shop', 'access': '가능', 'existing': '없음'}}}
    assert customer.post(path, json=form).status_code == 403
    sub = post(customer, path, {'kind': 'subscription', 'plan': 'lite', 'client': 'sub'})
    post(customer, path + '/' + sub['id'] + '/sandbox-confirm', {})
    order = post(customer, path, form)
    assert order['amount'] == 43000 and order['status'] == 'pending'
    assert post(customer, path, form)['id'] == order['id']
    post(customer, path + '/' + order['id'] + '/sandbox-confirm', {})
    post(customer, path + '/' + order['id'] + '/sandbox-refund', {'confirmed': True})
    form['client'] = 'review'
    form['details']['naver']['existing'] = '모름'
    review = post(customer, path, form)
    assert review['status'] == 'review'
    assert customer.post(path + '/' + review['id'] + '/sandbox-confirm', json={}).status_code == 409
    assert customer.get('/api/billing/assistance/queue').status_code == 403
