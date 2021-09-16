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
from datetime import datetime, timedelta
from eth_account import Account, messages


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
    if current_stage_index == len(config.stages):
        return Response({'status': 'ENDED'})
    if current_stage_index + 1 == len(config.stages):
        next_stage_price_usd = None
    else:
        next_stage_price_usd = config.stages[next_stage_index].price

    stage_end_timestamp = contract.functions.STAGES(current_stage_index).call()

    stage_start = datetime.fromtimestamp(stage_end_timestamp)
    today = datetime.now()
    print('today', today)
    print('stage start', stage_start)
    current_stage_days_left = (stage_start - today).days
    current_stage_tokens_sold = contract.functions.amounts(current_stage_index).call()
    current_stage_tokens_limit = contract.functions.LIMITS(current_stage_index).call()

    current_price_usd = config.stages[current_stage_index].price

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
    operation_description='Stages data view. Statuses are `CLOSED`, `ACTIVE` and `SOON`',
    responses={
        200: openapi.Response(
            description='Stages info response',
            schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                        'tokens_limit': openapi.Schema(type=openapi.TYPE_STRING),
                    },
                )
            )
        ),
    }
)
@api_view(http_method_names=['GET'])
def stages_view(request):
    contract = config.crowdsale_contract
    current_stage_index = contract.functions.determineStage().call()
    crowdsale_start_time = contract.functions.startTime().call()
    tokens_limits = contract.functions.allLimits().call()
    result = []
    for i in range(len(tokens_limits)):
        if not crowdsale_start_time:
            status = 'SOON'
        elif i < current_stage_index:
            status = 'CLOSED'
        elif i > current_stage_index:
            status = 'SOON'
        else:
            status = 'ACTIVE'

        stage = config.stages[i]
        result.append({
            'status': status,
            'price': stage.price,
            'name': stage.name,
            'tokens_limit': str(tokens_limits[i] * (10 ** 5))
        })

    return Response(result)


@swagger_auto_schema(
    method='GET',
    operation_description='Tokens view',
    responses={
        200: openapi.Response(
            description='Tokens info response',
            schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'symbol': openapi.Schema(type=openapi.TYPE_STRING),
                        'address': openapi.Schema(type=openapi.TYPE_STRING),
                        'decimals': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'price': openapi.Schema(type=openapi.TYPE_STRING),
                    },
                )
            )
        ),
    }
)
@api_view(http_method_names=['GET'])
def tokens_view(request):
    response = []
    for token in config.tokens:
        try:
            price = UsdRate.objects.get(symbol=token.cryptocompare_symbol).value
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


@swagger_auto_schema(
    method='POST',
    operation_description='Signature view',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'token_address': openapi.Schema(type=openapi.TYPE_STRING),
            'amount_to_pay': openapi.Schema(type=openapi.TYPE_STRING),
        },
        required=['token_address', 'amount_to_pay']
    ),
    responses={
        200: openapi.Response(
            description='Signature response',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'token_address': openapi.Schema(type=openapi.TYPE_STRING),
                    'amount_to_pay': openapi.Schema(type=openapi.TYPE_STRING),
                    'amount_to_receive': openapi.Schema(type=openapi.TYPE_STRING),
                    'signature_expiration_timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                    'signature': openapi.Schema(type=openapi.TYPE_STRING),
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
def signature_view(request):
    data = request.data
    token_address = data['token_address']
    amount_to_pay = int(data['amount_to_pay'])

    try:
        token_address_checksum = Web3.toChecksumAddress(token_address)
        token = config.get_token_by_address(token_address_checksum)
    except ValueError:
        return Response({'detail': 'INVALID_TOKEN_ADDRESS'}, status=400)

    contract = config.crowdsale_contract
    crowdsale_start_time = contract.functions.startTime().call()

    if not crowdsale_start_time:
        return Response({'detail': 'NOT_STARTED'}, status=400)

    current_stage_index = contract.functions.determineStage().call()
    current_price = config.stages[current_stage_index].price

    usd_rate = UsdRate.objects.get(symbol=token.cryptocompare_symbol)
    usd_amount_to_pay = amount_to_pay / usd_rate.value
    decimals = 10 ** (config.token_decimals - token.decimals)
    amount_to_receive = int(usd_amount_to_pay / current_price * decimals)

    signature_expires_at = datetime.now() + timedelta(minutes=config.signature_expiration_timeout_minutes)
    signature_expiration_timestamp = int(signature_expires_at.timestamp())
    print([token_address_checksum, amount_to_pay, amount_to_receive, signature_expiration_timestamp])
    keccak_hex = Web3.solidityKeccak(
        ['address', 'uint256', 'uint256', 'uint256'],
        [token_address_checksum, amount_to_pay, amount_to_receive, signature_expiration_timestamp]
    ).hex()

    message_to_sign = messages.encode_defunct(hexstr=keccak_hex)
    signature = Account.sign_message(message_to_sign, private_key=config.private_key)

    return Response({
        'token_address': token_address_checksum,
        'amount_to_pay': str(amount_to_pay),
        'amount_to_receive': str(amount_to_receive),
        'signature_expiration_timestamp': str(signature_expiration_timestamp),
        'signature': signature.signature.hex()
    })
