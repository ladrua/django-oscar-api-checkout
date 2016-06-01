from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from oscar.core.loading import get_model
from oscarapi.views.checkout import CheckoutView as OscarCheckoutView
from .settings import (
    API_ENABLED_PAYMENT_METHODS,
    ORDER_STATUS_PAYMENT_DECLINED,
    ORDER_STATUS_AUTHORIZED,
)
from .serializers import (
    CheckoutSerializer,
    OrderSerializer,
    PaymentMethodsSerializer,
    PaymentStateSerializer
)
from .signals import order_placed
from .states import COMPLETE, DECLINED
from . import utils

Order = get_model('order', 'Order')

CHECKOUT_ORDER_ID = 'checkout_order_id'


class PaymentMethodsView(generics.GenericAPIView):
    serializer_class = PaymentMethodsSerializer

    def get(self, request):
        serializer = self.get_serializer()
        data = self.metadata_class().get_serializer_info(serializer)
        return Response(data)


class CheckoutView(generics.GenericAPIView):
    """
    Checkout and use a WFRS account as payment.

    POST(basket, shipping_address, wfrs_source_account,
         [total, shipping_method_code, shipping_charge, billing_address]):
    {
        "basket": "/api/baskets/1/",
        "guest_email": "foo@example.com",
        "total": "100.0",
        "shipping_charge": {
            "currency": "EUR",
            "excl_tax": "10.0",
            "tax": "0.6"
        },
        "shipping_method_code": "no-shipping-required",
        "shipping_address": {
            "country": "/api/countries/NL/",
            "first_name": "Henk",
            "last_name": "Van den Heuvel",
            "line1": "Roemerlaan 44",
            "line2": "",
            "line3": "",
            "line4": "Kroekingen",
            "notes": "Niet STUK MAKEN OK!!!!",
            "phone_number": "+31 26 370 4887",
            "postcode": "7777KK",
            "state": "Gerendrecht",
            "title": "Mr"
        },
        "payment": {
            "cash": {
                "amount": "100.00"
            }
        }
    }

    Returns the order object.
    """
    serializer_class = CheckoutSerializer

    def post(self, request, format=None):
        # Wipe out any previous state data
        utils.clear_payment_method_states(request)

        # Validate the input
        c_ser = self.get_serializer(data=request.data)
        if not c_ser.is_valid():
            return Response(c_ser.errors, status.HTTP_406_NOT_ACCEPTABLE)

        # Freeze basket
        basket = c_ser.validated_data.get('basket')
        basket.freeze()

        # Save Order
        order = c_ser.save()
        request.session[CHECKOUT_ORDER_ID] = order.id

        # Save payment steps into session for processing
        states = self._record_payments(
            request=request,
            order=order,
            methods=c_ser.fields['payment'].methods,
            data=c_ser.validated_data['payment'])
        utils.set_payment_method_states(order, request, states)

        # Return order data
        order_placed.send(sender=self, order=order, user=request.user, request=request)
        o_ser = OrderSerializer(order, context={ 'request': request })
        return Response(o_ser.data)


    def _record_payments(self, request, order, methods, data):
        order_balance = [order.total_incl_tax]
        states = {}

        def record(code, method_data):
            method = methods[code]
            state = method.record_payment(request, order, **method_data)
            order_balance[0] = order_balance[0] - state.amount
            return state

        # Loop through each method with a specified amount to charge
        data_amount_specified = { k: v for k, v in data.items() if not v['pay_balance'] }
        for code, method_data in data_amount_specified.items():
            states[code] = record(code, method_data)

        # Change the remainder, not covered by the above methods, to the method marked with `pay_balance`
        data_pay_balance = { k: v for k, v in data.items() if v['pay_balance'] }
        for code, method_data in data_pay_balance.items():
            method_data['amount'] = order_balance[0]
            states[code] = record(code, method_data)

        return states


class PaymentStatesView(generics.GenericAPIView):
    def get(self, request, pk=None):
        # We don't really use the provided pk. It's just there to be compatible with oscarapi
        if pk and int(pk) != request.session.get(CHECKOUT_ORDER_ID):
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Fetch the order object from the session, but only if it's pending
        pk = request.session.get(CHECKOUT_ORDER_ID)
        order = get_object_or_404(Order, pk=pk)

        # Return order status and payment states
        states = utils.list_payment_method_states(request)
        state_data = {}
        for code, state in states.items():
            ser = PaymentStateSerializer(instance=state)
            state_data[code] = ser.data

        return Response({
            'order_status': order.status,
            'payment_method_states': state_data if any(state_data) else None
        })
