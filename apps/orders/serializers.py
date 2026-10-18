from rest_framework import serializers

from .models import Kot, Order, OrderItem, OrderTax, Payment


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'name', 'category_name', 'qty', 'price', 'discount', 'tax_rate', 'tax_amount', 'is_cancelled']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['mode', 'amount', 'reference_no']


class OrderTaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderTax
        fields = ['name', 'rate', 'amount']


class OrderSerializer(serializers.ModelSerializer):
    outlet_name = serializers.CharField(source='outlet.name', read_only=True)
    biller_name = serializers.CharField(source='biller.name', read_only=True, default='')
    net_sales = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    taxes = OrderTaxSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        exclude = ['device']


class KotSerializer(serializers.ModelSerializer):
    invoice_no = serializers.CharField(source='order.invoice_no', read_only=True)

    class Meta:
        model = Kot
        fields = ['id', 'order', 'invoice_no', 'number', 'lines', 'status', 'created_at']