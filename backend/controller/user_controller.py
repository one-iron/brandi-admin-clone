import pymysql
from jsonschema      import validate, ValidationError

from flask           import request, g
from connection      import get_connection
from utils           import authorize
from json_schema     import seller_register_schema


def create_user_endpoints(app, user_service):
    user_service = user_service

    @app.route('/sign-up', methods = ['POST'])
    def sign_up():

        """
        회원가입 API [POST]

        Args:
            [Body]
                user                : 셀러 id
                password            : 비밀번호
                phone_number        : 핸드폰번호
                seller_attribute_id : 셀러 정보 id (쇼핑몰 : 1, 마켓 : 2, 로드샵 : 3, 디자이너브랜드 : 4, 제너럴브랜드 : 5, 내셔널브랜드 : 6, 뷰티 : 7)
                name                : 셀러명 (상호)
                eng_name            : 영문 셀러명(영문상호)
                service_number      : 고객센터 전화번호
                site_url            : 사이트 URL

        Returns:

            success                : code : 200
            key error              : {message : KEY_ERROR}, code : 400

            셀러 ID 중복            : {message : USER_ALREADY_EXISTS}, code : 400
            셀러 ID 형식 위반       : {message : ID_VALIDATION_ERROR}, code :400
            비밀번호 형식 위반       : {message : PASSWORD_VALIDATION_ERROR}, code : 400
            핸드폰번호 형식 위반     : {message : PHONE_NUMBER_VALIDATION_ERROR}, code : 400
            셀러 이름 형식 위반      : {message : SELLER_NAME_VALIDATION_ERROR}, code : 400
            셀러 영문 이름 형식 위반 : {message : SELLER_ENGLISH_NAME_VALIDATION_ERROR}, code :400
            사이트 URL 형식 위반     : {message : SITE_URL_VALIDATION_ERROR}, code :400

        """

        db_connection = None
        try:
            db_connection = get_connection()
            new_user = request.json

            if db_connection:
                sign_up_response = user_service.sign_up_seller(new_user, db_connection)
                db_connection.commit()

                return sign_up_response

        except pymysql.err.InternalError:

            if db_connection:
                db_connection.rollback()

            return {'message' : 'DATABASE_SERVER_ERROR'}, 500

        except pymysql.err.OperationalError:
            return {'message' : 'DATABASE_ACCESS_DENIED'}, 500

        except pymysql.err.ProgrammingError as e:
            return {'message' : 'DATABASE_PROGRAMMING_ERROR' + str(e)}, 500

        except pymysql.err.NotSupportedError:
            return {'message' : 'DATABASE_NOT_SUPPORTED_ERROR'}, 500

        except pymysql.err.IntegrityError as e:
            db_connection.rollback()
            return {'message' : 'DATABASE_INTERGRITY_ERROR' + str(e)}, 500

        except Exception as e:
            db_connection.rollback()
            return {'message' : str(e)}, 500

        finally:
            if db_connection:
                db_connection.close()

    @app.route('/sign-in', methods=['POST'])
    def sign_in():

        """
        로그인 API [POST]

        Args:

        user        : 셀러 id
        password    : 비밀번호

        Returns:

        Success     : {access_token : token}, 200
        key error   : {message : KEY_ERROR}, code : 400

        로그인 ID 오류   : {'message' : 'USER_DOES_NOT_EXIST'}, code : 400
        비밀번호 불일치   : {'message' : 'INVALID ACCESS'}
        """

        db_connection = None
        get_user = request.json
        try:
            db_connection = get_connection()
            if db_connection:
                sign_in_response = user_service.check_user(get_user, db_connection)

                return sign_in_response

        except pymysql.err.InternalError:
            return {'message' : 'DATABASE_SERVER_ERROR'}, 500

        except pymysql.err.OperationalError:
            return {'message' : 'DATABASE_ACCESS_DENIED'}, 500

        except pymysql.err.ProgrammingError:
            return {'message' : 'DATABASE_PROGRAMMING_ERROR'}, 500

        except pymysql.err.NotSupportedError:
            return {'message' : 'DATABASE_NOT_SUPPORTED_ERROR'}, 500

        except pymysql.err.IntegrityError:
            return {'message' : 'DATABASE_INTERGRITY_ERROR'}, 500

        except  Exception as e:
            db_connection.rollback()
            return {'message' : str(e)}, 500

        finally:
            if db_connection:
                db_connection.close()

    @app.route('/sellers', methods=['GET'])
    @authorize
    def seller_list():

        """
        셀러 계정 관리 리스트 API [GET]

        Args:

        [Header] Authorization : 로그인 토큰

        Returns:

        Success     : {'number_of_sellers' : number_of_sellers,
                       'number_of_pages'   : number_of_pages,
                       'sellers'           : sellers }, 200
        key error   : {message : KEY_ERROR}, code : 400

        마스터 권한 아닐 시 : {'message' : 'UNAUTHORIZED'}, code : 400
        """

        if g.auth is not 1:
            return {'message' : 'UNAUTHORIZED'}, 401

        db_connection = None
        try:
            db_connection = get_connection()
            if db_connection:
                sellers = user_service.get_sellerlist(db_connection)

                if 400 in sellers:
                    return sellers

                return {'number_of_sellers' : len(sellers),
                            'number_of_pages' : int(len(sellers)/10)+1,
                            'sellers' : sellers,
                            }, 200

        except pymysql.err.InternalError:
            return {'message': 'DATABASE_SERVER_ERROR'}, 500

        except pymysql.err.OperationalError:
            return {'message': 'DATABASE_ACCESS_DENIED'}, 500

        except pymysql.err.ProgrammingError:
            return {'message': 'DATABASE_PROGRAMMING_ERROR'}, 500

        except pymysql.err.NotSupportedError:
            return {'message': 'DATABASE_NOT_SUPPORTED_ERROR'}, 500

        except pymysql.err.IntegrityError:
            return {'message': 'DATABASE_INTERGRITY_ERROR'}, 500

        except  Exception as e:
            return {'message': str(e)}, 500

        finally:
            if db_connection:
                db_connection.close()

    @app.route('/seller', methods=['PUT'])
    @authorize
    def update_seller():
        """
        셀러 수정 (셀러 권한) API [PUT]

        Args:

            [Header]
                Authorization : 로그인 토큰

            [Body]
                (기본 정보)
                profile : 셀러 프로필

                (상세정보)
                background_image    : 셀러페이지 배경이미지
                simple_introduction : 셀러 한줄 소개 (required)
                detail_introduction : 셀러 상세 소개
                site_url            : 사이트 URL
                bank                : 정산은행 (required)
                account_owner       : 계좌주 (required)
                bank_account        : 계좌번호 (required)
                order               : 순서
                service_number      : 고객센터 전화번호 (required)
                zip_code            : 우편번호
                address             : 주소 (택배 수령지)
                detail_address      : 상세주소 (택배 수령지) (required)

                (담당자 정보) (required)
                supervisor_name         : 담당자명
                supervisor_phone_number : 담당자 핸드폰번호
                supervisor_email        : 담당자 이메일

                (고객센터 운영시간)
                start_time : 9:00:00
                end_time   : 6:00:00
                is_weekend : 0    

                (배송정보 및 교환/환불 정보)
                shipping_information : 배송정보 (required)
                refund_information   : 교환 / 환불 정보 (required)

                (셀러 모델 사이즈 정보)
                model_height      : 키
                model_size_top    : 상의 사이즈
                model_size_bottom : 하의 사이즈
                model_size_foot   : 발 사이즈

                (쇼핑피드 업데이트 메세지)
                feed_message : 쇼핑피드 업데이트 메세지          

        Returns:
            Success : status code : 200

            Key error                          : {message : KEY_ERROR}, status code : 400
            Type error                         : {message : TYPE_ERROR}, status code : 400
            Request Parameter Validation Error : {message : PARAMETER_VALIDATION_ERROR}, status code : 400
        """
        db_connection = None
        seller_infos = request.json
        
        try: 
            validate(seller_infos, seller_register_schema)
            db_connection = get_connection()

            if db_connection:
                update_response = user_service.update_seller(g.user, seller_infos, db_connection)
                db_connection.commit()
                return update_response

        except  ValidationError as e:
            return {'message' : 'PARAMETER_VALIDATION_ERROR' + str(e)}, 400

        except pymysql.err.InternalError:
            return {'message' : 'DATABASE_SERVER_ERROR'}, 500

        except pymysql.err.OperationalError:
            return {'message' : 'DATABASE_ACCESS_DENIED'}, 500

        except pymysql.err.ProgrammingError as e:
            return {'message' : 'DATABASE_PROGRAMMING_ERROR' + str(e)}, 500

        except pymysql.err.NotSupportedError:
            return {'message' : 'DATABASE_NOT_SUPPORTED_ERROR'}, 500

        except pymysql.err.IntegrityError as e:
            return {'message' : 'DATABASE_INTERGRITY_ERROR' + str(e)}, 500

        except Exception as e:

            if db_connection:
                db_connection.rollback()

            return {'message' : str(e)}, 500

        finally:
            
            if db_connection:
                db_connection.close()

    @app.route('/seller_details', methods = ['GET'])
    @authorize
    def get_seller_details():

        """
        셀러 상세 (셀러 권한) API [GET]

        Args:
            [Header]`
                Authorization : 로그인 토큰

        Returns:

            Success     : {data : user_info}, status code : 200

            Key error   : {message : KEY_ERROR}, status code : 400
            Type error   :{message : TYPE_ERROR}, status code : 400
        """

        db_connection = None
        try:
            db_connection = get_connection()
            if db_connection:
                seller_infos = user_service.get_seller_details(g.user, db_connection)
                return seller_infos

        except pymysql.err.InternalError:
            return {'message' : 'DATABASE_SERVER_ERROR'}, 500

        except pymysql.err.OperationalError:
            return {'message' : 'DATABASE_ACCESS_DENIED'}, 500

        except pymysql.err.ProgrammingError:
            return {'message' : 'DATABASE_PROGRAMMING_ERROR'}, 500

        except pymysql.err.NotSupportedError:
            return {'message' : 'DATABASE_NOT_SUPPORTED_ERROR'}, 500

        except pymysql.err.IntegrityError:
            return {'message' : 'DATABASE_INTERGRITY_ERROR'}, 500

        except Exception as e:
            db_connection.rollback()
            return {'message' : str(e)}, 500

        finally:
            if db_connection:
                db_connection.close()
    
