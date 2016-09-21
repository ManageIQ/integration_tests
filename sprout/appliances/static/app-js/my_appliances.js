// my_appliances

var myAppliancesApp = angular.module('myAppliancesApp', []);

myAppliancesApp.config(function($interpolateProvider){
    $interpolateProvider.startSymbol('{[{').endSymbol('}]}');
});

myAppliancesApp.config(['$httpProvider', function($httpProvider) {
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';

}]);


myAppliancesApp.controller('EditVmName', function ($scope, $http, $timeout, $window) {
    $scope.$watch("applianceOriginalName", function(){
        $scope.saved = {"name": $scope.applianceOriginalName};
        $scope.vm = {"name": $scope.saved.name};
    });
    $scope.editing = false;
    $scope.submitting = false;

    $scope.save = function(vm) {
        var responsePromise = $http.post(
            $scope.apiURL, {appliance_id: $scope.applianceId, new_name: vm.name});

        $scope.submitting = true;

        responsePromise.success(function(data, status, headers, config) {
            addAlert("success", "Task " + data + " queued.");
            $scope.taskId = data;
            (function waitUntilRenamed(){
                var taskFinishedPromise = $http.post($scope.taskResultURL, {task_id: $scope.taskId});
                taskFinishedPromise.success(function(data, status, headers, config) {
                    if(data !== null){
                        addAlert("success", "The appliance was renamed to " + data);
                        $scope.taskId = null;
                        $scope.vm.name = data;
                        $scope.saved.name = data;
                        $scope.submitting = false;
                        $scope.editing = false;
                    } else {
                        $timeout(waitUntilRenamed, 1000);
                    }
                });

                taskFinishedPromise.error(function(data, status, headers, config) {
                    addAlert("danger", "Could not rename the VM!");
                    $scope.submitting = false;
                });
            })();
        });

        responsePromise.error(function(data, status, headers, config) {
            addAlert("danger", data);
        });
     };

    $scope.cancel = function() {
       angular.copy($scope.saved, $scope.vm);
       $scope.editing = false;
     };

    $scope.edit = function() {
        if(! $scope.applianceHasUUID) {
            // No change, we can edit only when we have UUID to be 100% sure
            $window.alert("Appliance " + $scope.applianceOriginalName + " did not receive its UUID yet so it cannot be renamed.");
            return;
        }
        $scope.vm = angular.copy($scope.saved);
        $scope.editing = true;
    };
});

myAppliancesApp.controller('EditExpiration', function ($scope) {
    $scope.defaultTimeout = true;
    $scope.expiration = 60;

    $scope.expDays = 0;
    $scope.expHours = 1;
    $scope.expMins = 0;

    updateForm = function() {
        if($scope.defaultTimeout) {
            $scope.expiration = 60;
        } else {
            $scope.expiration = $scope.expMins + 60*$scope.expHours + 60*24*$scope.expDays;
        }
    }

    $scope.$watch("defaultTimeout", updateForm);
    $scope.$watch("expDays", updateForm);
    $scope.$watch("expHours", updateForm);
    $scope.$watch("expMins", updateForm);
});