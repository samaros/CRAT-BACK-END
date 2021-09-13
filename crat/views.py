from rest_framework.decorators import api_view
from rest_framework.response import Response
from crat.settings import config
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from datetime import datetime
from crat.models import UsdRate, Investor
from web3 import Web3
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.core.validators import validate_email


current_stage_response = openapi.Response(
    description='Current stage info. Statuses are `NOT_STARTED`, `ACTIVE` and `ENDED`',
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'status': openapi.Schema(type=openapi.TYPE_STRING),
            'current_stage_price_usd': openapi.Schema(type=openapi.TYPE_NUMBER),
            'current_stage_number': openapi.Schema(type=openapi.TYPE_INTEGER),
            'current_stage_days_left':  openapi.Schema(type=openapi.TYPE_INTEGER),
            'current_stage_tokens_sold': openapi.Schema(type=openapi.TYPE_STRING),
            'current_stage_tokens_limit': openapi.Schema(type=openapi.TYPE_STRING),
            'next_stage_price_usd': openapi.Schema(type=openapi.TYPE_NUMBER),
        },
    )
)

crowdsale_ended_response = openapi.Response(
    description='Сrowdsale is over',
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'detail': openapi.Schema(type=openapi.TYPE_STRING),
        },
    )
)


@swagger_auto_schema(
    method='GET',
    operation_description='Stage data view',
    responses={200: current_stage_response}
)
@api_view(http_method_names=['GET'])
def stage_view(request):
    contract = config.crowdsale_contract
    current_stage_index = contract.functions.determineStage().call()

    crowdsale_start_time = contract.functions.startTime().call()

    if not crowdsale_start_time:
        return Response({'status': 'NOT_STARTED'})

    next_stage_index = current_stage_index + 1
    if current_stage_index == len(config.prices):
        return Response({'status': 'ENDED'})
    if current_stage_index + 1 == len(config.prices):
        next_stage_price_usd = None
    else:
        next_stage_price_usd = config.prices[next_stage_index]

    if current_stage_index > 0:
        stage_start_timestamp = contract.functions.STAGES(current_stage_index-1).call()
    else:
        stage_start_timestamp = crowdsale_start_time

    stage_start = datetime.fromtimestamp(stage_start_timestamp)
    today = datetime.now()
    print('today', today)
    print('stage start', stage_start)
    current_stage_days_left = (today - stage_start).days
    current_stage_tokens_sold = contract.functions.amounts(current_stage_index).call()
    current_stage_tokens_limit = contract.functions.LIMITS(current_stage_index).call()

    current_price_usd = config.prices[current_stage_index]

    return Response({
        'status': 'ACTIVE',
        'current_stage_price_usd': current_price_usd,
        'current_stage_number': current_stage_index + 1,
        'current_stage_days_left':  current_stage_days_left,
        'current_stage_tokens_sold': current_stage_tokens_sold // (10 ** config.token_decimals),
        'current_stage_tokens_limit': current_stage_tokens_limit * (10 ** 5),
        'next_stage_price_usd': next_stage_price_usd,
    })


@swagger_auto_schema(
    method='GET',
    operation_description='Tokens view',
)
@api_view(http_method_names=['GET'])
def tokens_view(request):
    response = []
    for token in config.tokens:
        try:
            price = UsdRate.objects.get(symbol=token.symbol).value
        except UsdRate.DoesNotExist:
            price = None

        token_serialized = {
            'symbol': token.symbol,
            'address': token.address,
            'decimals': token.decimals,
            'price': '{:.2f}'.format(1 / price),
        }
        response.append(token_serialized)

    return Response(response)


@swagger_auto_schema(
    method='POST',
    operation_description='Whitelist view',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'address': openapi.Schema(type=openapi.TYPE_STRING),
            'email': openapi.Schema(type=openapi.TYPE_STRING),
        },
        required=['address', 'email']
    ),
    responses={
        200: openapi.Response(
            description='Whitelist success reponse',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                },
            )
        ),
        400: openapi.Response(
            description='Invalid parameters response',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                },
            )
        ),
    }
)
@api_view(http_method_names=['POST'])
def whitelist_view(request):
    data = request.data
    address = data['address']
    email = data['email']

    try:
        validate_email(email)
    except ValidationError:
        return Response({'detail': 'INVALID_EMAIL'}, status=400)

    try:
        address = Web3.toChecksumAddress(address)
    except ValueError:
        return Response({'detail': 'INVALID_ADDRESS'}, status=400)

    try:
        Investor(address=address, email=email).save()
    except IntegrityError:
        return Response({'detail': 'ALREADY_REGISTERED'}, status=400)

    return Response({'detail': 'OK'})


@swagger_auto_schema(
    method='GET',
    operation_description='Is whitelisted view',
    responses={
        200: openapi.Response(
            description='Is address whitelisted',
            schema=openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
            )
        ),
        400: openapi.Response(
            description='Invalid address response',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                },
            )
        )
    }
)
@api_view(http_method_names=['GET'])
def is_whitelisted_view(request, address):

    try:
        address = Web3.toChecksumAddress(address)
    except ValueError:
        return Response({'detail': 'INVALID_ADDRESS'}, status=400)

    is_whitelisted = Investor.objects.filter(address=address).exists()
    return Response(is_whitelisted)
