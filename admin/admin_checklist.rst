관리자 체크리스트
===================

참가자별 ``pNNN``을 실제 번호로 변경해 사용합니다.
상세 절차는 `관리자 준비 가이드 <README.md>`__를 확인합니다.

공통 운영 준비
--------------

상세: `리소스 <README.md#준비할-리소스>`__ ·
`비용 <README.md#예상-비용>`__ ·
`네트워크 <README.md#5-네트워크>`__

- [ ] 참가자 수·동시 실행량 기준 Fabric F 용량 규모 확정
- [ ] Fabric 용량 활성화·Pause 담당자 및 운영 시간 확정
- [ ] Databricks·Fabric·Teams·Foundry용 Microsoft Entra ID 계정 확인
- [ ] Serverless의 OneLake·PyPI·Microsoft Entra HTTPS(443) 연결 확인

Azure Databricks 준비
---------------------

상세: `Unity Catalog와 Serverless <README.md#1-unity-catalog와-serverless>`__ ·
`Managed Identity와 service credential <README.md#2-managed-identity와-service-credential>`__

- [ ] Premium workspace의 Unity Catalog 메타스토어 연결
- [ ] Notebook Serverless 지원 지역·Workspace access 확인
- [ ] Unity Catalog 메타스토어 기본 관리형 저장소 설정
- [ ] ``01_setup`` 자동 생성용 메타스토어 ``CREATE CATALOG`` 권한 부여
- [ ] Access Connector ``ac-chipbalance-onelake`` 생성
- [ ] service credential ``chipbalance_onelake_hyosung`` 생성·``GRANT ACCESS`` 적용
- [ ] ``notebooks\ChipBalance.zip``의 **Workspace → Shared → ChipBalance** Import
- [ ] 실행 결과 없는 Notebook 8개 확인
- [ ] Shared의 ``ChipBalance/fabric``에 TMDL·테마·승인 Notebook 3개 배치
- [ ] 참가자 읽기·Clone·파일 내려받기 권한 부여
- [ ] 선택 Genie용 ``chipbalance-pro``·OneLake Federation·데이터 권한 준비

Microsoft Fabric 준비
---------------------

상세: `Microsoft Fabric <README.md#3-microsoft-fabric>`__

- [ ] 참가자별 작업 영역 ``chipbalance-pNNN`` 생성·유료 용량 할당
- [ ] Lakehouse schemas를 켠 ``lh_chipbalance_pNNN`` 생성
- [ ] 참가자와 ``ac-chipbalance-onelake``의 작업 영역 Contributor 권한 부여
- [ ] OneLake 외부 앱·Service Principal API 테넌트 설정 허용
- [ ] Fabric 항목·Ontology·Copilot·AI Agents 테넌트 설정 허용
- [ ] Data agent의 Ontology 추가·바인딩 원본 읽기 권한과 원본별 지침 저장 확인
- [ ] Power BI Pro 또는 PPU와 모델·보고서 작성 권한 준비

Microsoft Teams 준비
--------------------

상세: `Microsoft Fabric <README.md#3-microsoft-fabric>`__

- [ ] 참가자 Teams 라이선스 확인
- [ ] **Fabric Operations Agent** 앱 허용

Microsoft Foundry 준비
----------------------

상세: `Microsoft Foundry <README.md#4-microsoft-foundry>`__

- [ ] Azure 구독·리소스 그룹·지원 지역 확정
- [ ] 참가자 리소스 그룹 Contributor 역할 부여
- [ ] ``fdy-chipbalance-pNNN``·``chipbalance-pNNN`` 생성 권한 확인
- [ ] Foundry User·Foundry Project Manager 역할 부여
- [ ] Fabric IQ 지원 모델 배포·할당량 확인
- [ ] managed OAuth 또는 BYO Microsoft Entra 연결·동의 준비

참가자 전달값·파일
------------------

상세: `전달값 <README.md#6-참가자에게-알려-줄-값>`__ ·
`파일 준비 <../docs/00-scenario.md#실습-파일-준비>`__

- [ ] Databricks 주소·실습 계정·참가자 번호 ``pNNN`` 전달
- [ ] **Workspace → Shared → ChipBalance** Clone 경로 전달
- [ ] Shared의 ``ChipBalance/fabric`` 파일 내려받기 방법 전달
- [ ] ``chipbalance-pNNN``·``lh_chipbalance_pNNN`` 이름 전달
- [ ] service credential ``chipbalance_onelake_hyosung`` 이름 전달
- [ ] Foundry 구독·리소스 그룹·지역 전달
- [ ] 선택 Genie용 ``fabric_chipbalance_pNNN``·``chipbalance-pro`` 안내

실습 당일 운영
--------------

상세: `관리자 확인 <README.md#6-참가자에게-알려-줄-값>`__

- [ ] Fabric 용량 활성 상태·작업 영역 할당 확인
- [ ] Shared의 Notebook·Fabric 파일 배포본 변경 중지
- [ ] 선택 Genie 운영 시 ``chipbalance-pro`` 사용 가능 상태 확인

종료 후 정리
------------

상세: `관리자 정리 <README.md#7-종료-후-정리>`__ ·
`참가자 마무리 <../docs/13-finish.md#2-감시와-실행-멈추기>`__

- [ ] 참가자별 ``oa_chipbalance`` Stop 확인
- [ ] SQL warehouse ``chipbalance-pro`` Stop
- [ ] 참가자별 Fabric 항목·작업 영역 보존 또는 삭제
- [ ] 선택 Genie Foreign catalog·Connection 의존성 확인 후 삭제
- [ ] Unity Catalog·스키마·Volume 보존 또는 삭제
- [ ] Foundry 리소스 삭제·필요 시 purge
- [ ] Fabric 용량 Pause
- [ ] ``ac-chipbalance-onelake`` 작업 영역 권한 정리
- [ ] 공용 credential·Access Connector 의존성 확인 후 삭제
